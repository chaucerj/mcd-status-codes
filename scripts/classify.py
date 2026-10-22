#!/usr/bin/env python3
"""麦门状态码分类器：把每笔订单判定为一个 HTTP 状态码。

输入: data/orders.parsed.json + data/nutrition_foods.json
输出: data/classified.json

语义唯一视角（详见 codes.py 语义宪法）：你是主体，你的身体是服务端。
全部规则为确定性函数，数值不进 LLM，结果可逐单复算。
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from codes import (
    BIG_ORDER_QTY, CODE_META, EASTER_EGG_404, KCAL_OK, KCAL_OVERLOAD,
    NIGHT_END, NIGHT_START, RULES_VERSION, SODIUM_DENIED,
    STREAK_ALERT, is_drink, label, normalize,
)


def match_nutrition(item_name: str, nutrition_index: dict) -> dict | None:
    """品名 → 营养表条目。精确 → 归一化精确 → 与营养表名双向包含（两侧均 ≥3 字）。

    只比较归一化品名与营养表名，禁止同串自比较（否则任意名称都会命中自己）。
    """
    norm = normalize(item_name)
    if item_name in nutrition_index:
        return nutrition_index[item_name]
    if norm in nutrition_index:
        return nutrition_index[norm]
    if len(norm) < 3:
        return None
    for name, row in nutrition_index.items():
        if len(name) >= 3 and (name in norm or norm in name):
            return row
    return None


def load_nutrition_index(path: Path) -> dict:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {r["productName"]: r for r in rows}


def load_image_index() -> dict:
    """官方餐品图缓存（来源：MCP 菜单接口，collect 阶段落盘 trial_menu.json）。

    键为归一化品名。订单本体不带图时，前端官方图/回退磁贴全靠这里补。"""
    path = Path(__file__).resolve().parent.parent / "data" / "trial_menu.json"
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    items = rows if isinstance(rows, list) else rows.get("items", [])
    idx = {}
    for r in items:
        name = r.get("name") or r.get("productName")
        img = r.get("img") or r.get("productImage")
        if name and img:
            idx[normalize(name)] = img
    return idx


_SIZE_QUAL = re.compile(r"(大|中|小)(杯|份)")


def _core(name: str) -> str:
    """规格弱化：去连字符、去 大/中/小+杯份、去单字规格前缀，便于跨规格对同一张图。"""
    s = re.sub(r"[\-–—]", "", normalize(name))
    s = _SIZE_QUAL.sub("", s)
    return re.sub(r"^(大|中|小)", "", s)


def match_image(item_name: str, image_index: dict) -> str:
    """品名 → 官方图 URL。层级：归一化精确 → 规格弱化精确 → 最长公共前缀（≥4 字，
    吃掉「麦辣鸡腿堡/麦辣鸡腿汉堡」这类同系变体）→ 双向包含（菜单侧 ≥3 字）
    → 头尾缀匹配（菜单侧 2 字如「新地」「可乐」）。"""
    if not image_index:
        return ""
    norm = normalize(item_name)
    if norm in image_index:
        return image_index[norm]
    core_map = {_core(k): v for k, v in image_index.items()}
    core = _core(norm)
    if core in core_map:
        return core_map[core]
    best_img, best_len, best_key = "", 0, ""
    for k, img in core_map.items():
        n = 0
        for a, b in zip(core, k):
            if a != b:
                break
            n += 1
        if n > best_len or (n == best_len and k and len(k) < len(best_key)):
            best_img, best_len, best_key = img, n, k
    if best_len >= 4:
        return best_img
    if len(norm) >= 3:
        for name, img in image_index.items():
            if len(name) >= 3 and (name in norm or norm in name):
                return img
    for name, img in image_index.items():
        if len(name) == 2 and len(norm) >= 4 and (norm.startswith(name) or norm.endswith(name)):
            return img
    return ""


def build_reason(status: str, ctx: dict) -> str:
    """生成诊断文案。

    约定：文案主语必须是「你/你的身体」；平台侧事实仅作证据补充。
    """
    if status == "504":
        return f"订单状态为「{ctx['rawStatus']}」，这次摄入最终没有发生，链路在上游超时中止"
    if status == "429":
        return f"当日第 {ctx['nth']} 单，你向身体发起了多次摄入请求，已被自身限流"
    if status == "408":
        return f"{ctx['hhmm']} 发起摄入请求，但你的身体已不在服务时段"
    if status == "418":
        return "整单只有饮品，你的身体这次只出茶壶不出餐"
    if status == "500":
        return f"单餐 {ctx['kcal']} kcal，超出身体的处理能力，服务当场过载"
    if status == "403":
        return f"营养署拒绝放行（{ctx['kcal']} kcal / 钠 {ctx['sodium']} mg），超出单餐配额"
    if status == "502":
        return f"本次请求聚合了 {ctx['qty']} 件商品，单次摄入量过大"
    if status == "304":
        return "与上一单逐项相同，你的身体直接复用了上次的摄入响应"
    if status == "301":
        return f"取餐路径由「{ctx['prevType']}」永久改道至「{ctx['orderType']}」"
    if status == "201":
        return f"你吃到了历史上从未出现过的单品（{ctx['newNames']}），身体新建了一条记录"
    if status == "206":
        return (f"{ctx['matched']}/{ctx['total']} 项能在你的营养账本中定位，"
                f"响应残缺（{ctx['coverage']} 可计量）")
    if status == "200":
        return f"{ctx['kcal']} kcal / 钠 {ctx['sodium']} mg，全部商品已入账且在配额内"
    return ""


def classify_order(orders_raw: list, nutrition_index: dict, image_index: dict | None = None) -> list:
    """按时间正序逐单判定。返回 enriched 订单列表。"""
    result = []
    seen_names: set = set()          # 历史已出现过的归一化品名
    prev_signature = None            # 上一单的商品签名（304 判定）
    prev_order_type = None           # 上一单渠道（301 判定）
    per_date_count: dict = {}        # 当日已见单数（429 判定）

    for o in sorted(orders_raw, key=lambda x: x["createTime"]):
        dt = datetime.strptime(o["createTime"], "%Y-%m-%d %H:%M:%S")
        items = []
        for p in o.get("orderProductList", []):
            row = match_nutrition(p["productName"], nutrition_index)
            qty = int(p.get("quantity", 1))
            items.append({
                "name": p["productName"],
                "img": p.get("productImage", "") or match_image(p["productName"], image_index or {}),
                "qty": qty,
                "matched": row is not None,
                "kcal": int(row["energyKcal"]) * qty if row else None,
                "sodium": int(row["sodium"]) * qty if row else None,
                "protein": round(float(row["protein"]) * qty) if row else None,
            })

        matched = [i for i in items if i["matched"]]
        kcal = sum(i["kcal"] for i in matched) if matched else None
        sodium = sum(i["sodium"] for i in matched) if matched else None
        protein = sum(i["protein"] for i in matched if i["protein"] is not None) if matched else None
        total_qty = sum(i["qty"] for i in items)
        signature = ",".join(sorted(f"{normalize(i['name'])}x{i['qty']}" for i in items))
        date_key = dt.strftime("%Y-%m-%d")
        per_date_count[date_key] = per_date_count.get(date_key, 0) + 1
        nth_today = per_date_count[date_key]
        new_names = [i["name"] for i in items if normalize(i["name"]) not in seen_names]

        # 指标告警（v4.0）：营养负荷超标记 breaches，不改变状态码
        breaches = []
        if kcal is not None and kcal > KCAL_OVERLOAD:
            breaches.append("calorie_overload")
        elif kcal is not None and kcal > KCAL_OK:
            breaches.append("calorie_over")
        if sodium is not None and sodium > SODIUM_DENIED:
            breaches.append("sodium_over")

        # 判定阶梯：首个命中即停（集合层 404 不在此列，见 build_summary）
        if "取消" in o.get("orderStatus", ""):
            status = "504"
        elif nth_today > 1:
            status = "429"
        elif dt.hour >= NIGHT_START or dt.hour < NIGHT_END:
            status = "408"
        elif items and all(is_drink(i["name"]) for i in items):
            status = "418"
        elif total_qty >= BIG_ORDER_QTY:
            status = "502"
        elif prev_signature is not None and signature == prev_signature:
            status = "304"
        elif prev_order_type is not None and o["orderType"] != prev_order_type:
            status = "301"
        elif new_names:
            status = "201"
        else:
            status = "206"

        reason = build_reason(status, {
            "rawStatus": o.get("orderStatus", ""), "nth": nth_today,
            "hhmm": dt.strftime("%H:%M"), "kcal": kcal, "sodium": sodium,
            "qty": total_qty, "prevType": prev_order_type,
            "orderType": o.get("orderType", ""), "newNames": "、".join(new_names[:2]),
            "matched": len(matched), "total": len(items),
            "coverage": f"{len(matched)}/{len(items)}" if items else "0/0",
        })

        for i in items:
            seen_names.add(normalize(i["name"]))
        prev_signature = signature
        prev_order_type = o["orderType"]

        result.append({
            "orderId": o["orderId"],
            "datetime": o["createTime"],
            "date": date_key,
            "hour": dt.hour,
            "store": o.get("storeName", ""),
            "orderType": o.get("orderType", ""),
            "rawStatus": o.get("orderStatus", ""),
            "amount": o.get("realTotalAmount", ""),
            "items": items,
            "kcal": kcal,
            "sodium": sodium,
            "protein": protein,
            "matchCoverage": f"{len(matched)}/{len(items)}" if items else "0/0",
            "breaches": breaches,
            "httpStatus": status,
            "codeLabel": label(status),
            "codeTitle": CODE_META[status]["title"],
            "codeMeaning": CODE_META[status]["meaning"],
            "reason": reason,
        })
    return result


def build_summary(orders: list) -> dict:
    # ── 集合层 404：订单集合为空 → 资源不存在，触发彩蛋 ──────────────────
    if not orders:
        return {
            "collectionStatus": "404",
            "collectionLabel": label("404"),
            "collectionTitle": CODE_META["404"]["title"],
            "easterEgg": EASTER_EGG_404,
            "spanDays": 0, "orderedDays": 0, "uptime": 0.0, "totalOrders": 0,
            "distribution": {}, "kcalP50": None, "kcalP99": None, "totalKcal": 0,
            "flowUnit": "0 KB", "ledgerCoverageRate": 0.0, "missedItems": [],
            "itemLedgerGapRate": 0.0, "missedDays": 0, "errorBudgetUsed": 0,
            "alerts": [], "days": [],
        }

    dates = sorted({o["date"] for o in orders})
    first = datetime.strptime(dates[0], "%Y-%m-%d")
    last = datetime.strptime(dates[-1], "%Y-%m-%d")
    span_days = (last - first).days + 1
    ordered_days = len(dates)
    day_set = set(dates)
    days = [{"date": (first + timedelta(days=i)).strftime("%Y-%m-%d"),
             "ordered": (first + timedelta(days=i)).strftime("%Y-%m-%d") in day_set}
            for i in range(span_days)]

    dist: dict = {}
    for o in orders:
        dist[o["httpStatus"]] = dist.get(o["httpStatus"], 0) + 1

    kcals = sorted(o["kcal"] for o in orders if o["kcal"] is not None)

    def pct(p):
        return kcals[min(len(kcals) - 1, int(len(kcals) * p))] if kcals else None

    # ── 营养账本覆盖率（原「商品级404 率」）：现为独立指标，非状态码 ──────
    total_items = sum(len(o["items"]) for o in orders)
    lost_items = sum(1 for o in orders for i in o["items"] if not i["matched"])
    lost_names: dict = {}
    for o in orders:
        for i in o["items"]:
            if not i["matched"]:
                lost_names[i["name"]] = lost_names.get(i["name"], 0) + i["qty"]

    total_kcal = sum(kcals) if kcals else 0
    kb = total_kcal / 1024
    flow = (f"{kb/1024/1024:.2f} GB" if kb >= 1024**2
            else (f"{kb/1024:.1f} MB" if kb >= 1024 else f"{kb:.1f} KB"))

    # 告警：最长 304 连击、429、408、账本缺口
    max_304_streak = streak = 0
    for o in orders:
        streak = streak + 1 if o["httpStatus"] == "304" else 0
        max_304_streak = max(max_304_streak, streak)
    alerts = []
    if max_304_streak >= STREAK_ALERT:
        alerts.append(f"⚠️ 连续 {max_304_streak} 单 304：缓存从未失效，建议刷新口味")
    if dist.get("429"):
        alerts.append(f"⚠️ {dist['429']} 次 429 限流：单日多单摄入行为被记录")
    if dist.get("408"):
        alerts.append(f"⚠️ {dist['408']} 次 408：深夜时段仍在发起摄入请求")
    if total_items:
        alerts.append(
            f"📡 营养账本缺口：{total_items} 件商品中 {lost_items} 件"
            f"无法在你的身体账本中计量（独立指标，不计错误预算）"
        )

    err = sum(v for k, v in dist.items() if k.startswith(("4", "5")) and k != "206")
    return {
        "collectionStatus": "200",
        "collectionLabel": label("200"),
        "collectionTitle": CODE_META["200"]["title"],
        "spanDays": span_days,
        "orderedDays": ordered_days,
        "uptime": round(ordered_days / span_days * 100, 1),
        "totalOrders": len(orders),
        "distribution": dist,
        "kcalP50": pct(0.5),
        "kcalP99": pct(0.99),
        "totalKcal": total_kcal,
        "flowUnit": flow,
        "ledgerCoverageRate": round((total_items - lost_items) / total_items * 100, 1) if total_items else 0,
        "itemLedgerGapRate": round(lost_items / total_items * 100, 1) if total_items else 0,
        "missedItems": sorted(lost_names.items(), key=lambda x: -x[1])[:8],
        "missedDays": span_days - ordered_days,
        "errorBudgetUsed": err,
        "alerts": alerts,
        "days": days,
    }


def main():
    base = Path(__file__).resolve().parent.parent
    orders_path = base / "data" / "orders.parsed.json"
    nutrition_path = base / "data" / "nutrition_foods.json"
    if len(sys.argv) > 1:  # demo 模式或指定输入
        orders_path = Path(sys.argv[1])
    if not orders_path.exists():
        raise SystemExit("缺少输入文件：先运行 scripts/collect.py（或指定已解析的订单 JSON）")

    orders_raw = json.loads(orders_path.read_text(encoding="utf-8"))["data"]["list"]
    nutrition_index = load_nutrition_index(nutrition_path)
    orders = classify_order(orders_raw, nutrition_index, load_image_index())
    summary = build_summary(orders)

    out = {"rulesVersion": RULES_VERSION,
           "dataset": "demo" if "demo" in str(orders_path) else "live",
           "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           "orders": list(reversed(orders)), "summary": summary}
    out_path = base / "data" / "classified.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    if summary["collectionStatus"] == "404":
        print("404 Not Found · 订单集合为空")
        for line in EASTER_EGG_404["lines"]:
            print(f"  {line}")
        print(f"\n{EASTER_EGG_404['cta']}")
        print(f"\n已写入 {out_path}")
        return

    print(f"共 {len(orders)} 单，分布：")
    for code in sorted(summary["distribution"], reverse=True):
        print(f"  {label(code):<24} × {summary['distribution'][code]}")
    print(f"\nUptime {summary['uptime']}%（{summary['orderedDays']}/{summary['spanDays']} 天）")
    print(f"营养账本覆盖率：{summary['ledgerCoverageRate']}%（缺口 {summary['itemLedgerGapRate']}%）")
    print(f"总摄入 {summary['totalKcal']} kcal ≈ {summary['flowUnit']}（1024 进制）")
    for a in summary["alerts"]:
        print(a)
    print(f"\n已写入 {out_path}")


if __name__ == "__main__":
    main()