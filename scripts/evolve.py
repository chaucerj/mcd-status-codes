#!/usr/bin/env python3
"""自进化循环：每次运行 = 麦门世界运维的一次「交接班」。

输入: data/classified.json + data/prefs.json（含 profile 代谢档案）+ data/nutrition_foods.json
输出: data/ops.json（事故复盘 / 口味画像 / 代谢模型 / 探活队列 / 洞察 / 职级 / 进化日志）
副作用: prefs.json 的 learned 区自动更新（确定性学习，不进 LLM）；
        changelog 追加本次进化记录。

v3.0 新增：probe 探活方向（语义见 codes.py 宪法 v3.0）——
  Agent 依据代谢模型在补给窗口内主动向你的身体发起探活：
  103 建议下发 / 204 主动静默 / 412 被目标否决 / 425 过早打扰 /
  599 建议窗口超时 / 522 连续窗口失联。
  采纳与否由后续订单确定性判定，形成闭环。
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from codes import (KCAL_OK, KCAL_OVERLOAD, SODIUM_DENIED,  # noqa: E402
                   CODE_META, PROBE_WINDOWS, METRIC_ALERTS)

# 口味关键词 → 画像标签（确定性聚合）
TASTE_KEYWORDS = {
    "嗜辣系": ["麦辣", "辣", "藤椒", "甜辣"],
    "禽类偏好": ["鸡"],
    "牛肉偏好": ["牛", "巨无霸", "吉士"],
    "猪肉系": ["猪柳"],
    "鳕鱼系": ["鳕鱼", "麦香鱼"],
    "咖啡因依赖": ["咖啡", "拿铁", "美式", "摩卡", "茶", "奶茶"],
    "甜品胃": ["新地", "圆筒", "冰淇淋", "派", "旋风", "朱古力", "松饼"],
    "冰饮党": ["可乐", "雪碧", "芬达", "冰", "椰饮"],
    "薯条原教旨": ["薯条"],
}
CAFFEINE_KEYWORDS = ["咖啡", "拿铁", "美式", "摩卡"]

# 事故根因与改进建议（确定性映射，per 状态码）
POSTMORTEM = {
    "504": {"cause": "上游请求中止：订单在完成前被取消", "advice": "下单前核对门店营业状态与取餐时段；预约单提前确认场次"},
    "429": {"cause": "短时重复写入：同日多次下单触发限流", "advice": "合并需求一次下单；错开与上一单的间隔"},
    "408": {"cause": "深夜窗口收到摄入请求", "advice": "22:00 后改轻量补给；把大餐挪进白天窗口"},
    "418": {"cause": "纯饮料请求命中茶壶协议", "advice": "补水即可，无需经麦门"},
    "304": {"cause": "缓存命中：与上一单完全一致", "advice": "轮换 1 个单品打破缓存，避免味觉回路固化"},
    "502": {"cause": "多人聚合网关：单笔承载过多上游", "advice": "拆分为多单分别结算，便于按人分摊"},
}
SEV = {"504": "P1", "429": "P2", "408": "P2", "502": "P3", "418": "P3", "304": "P3"}

LEVELS = [
    (95, "麦门世界 CTO", "你的身体服务进入了 SLA 黄金档，可以给别人做 postmortem 了"),
    (88, "首席 on-call", "事故到你手里都能优雅降级"),
    (75, "资深 SRE", "告警页大部分时候是绿的"),
    (60, "正式运维", "值班手机响得少了"),
    (40, "初级运维", "至少背锅时知道查日志了"),
    (0, "实习 on-call", "重生第一课：身体服务也是服务"),
]

ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "high": 1.725}


def load(path, default):
    p = BASE / "data" / path
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


# ── 代谢模型（Mifflin-St Jeor，确定性）─────────────────────────────
def metabolic(prefs):
    p = prefs.get("profile") or {}
    if not (p.get("weight") and p.get("height") and p.get("age")):
        return {"profileSet": False,
                "hint": "在 data/prefs.json 填入 profile（体重/身高/年龄/性别/活动系数/场景），"
                        "即可开启 TDEE 代谢探活"}
    sex = p.get("sex", "male")
    bmr = 10 * p["weight"] + 6.25 * p["height"] - 5 * p["age"] + (5 if sex == "male" else -161)
    tdee = round(bmr * ACTIVITY.get(p.get("activity"), 1.375))
    goal = p.get("goal", "keep")
    target = round(tdee - 400) if goal == "cut" else round(tdee + 300) if goal == "bulk" else tdee
    return {"profileSet": True, "bmr": round(bmr), "tdee": tdee,
            "goal": goal, "target": target,
            "windows": {"breakfast": round(target * .3), "lunch": round(target * .4),
                        "dinner": round(target * .25), "snack": round(target * .05)}}


def taste_profile(orders):
    total = len(orders)
    out = []
    for label, kws in TASTE_KEYWORDS.items():
        hits = sum(1 for o in orders
                   if any(k in i["name"] for i in o["items"] for k in kws))
        if hits:
            out.append({"label": label, "orders": hits,
                        "rate": round(hits / total * 100)})
    return sorted(out, key=lambda x: -x["orders"])


def habits(orders):
    nights = sum(1 for o in orders if o["hour"] >= 22 or o["hour"] < 5)
    budgets = [float(o["amount"]) for o in orders if o.get("amount")]
    combos = {}
    for o in orders:
        sig = "+".join(sorted(i["name"] for i in o["items"]))
        combos.setdefault(sig, {"items": [i["name"] for i in o["items"]], "count": 0})
        combos[sig]["count"] += 1
    top = sorted(combos.values(), key=lambda x: -x["count"])[:3]
    return {"nightRate": round(nights / len(orders) * 100) if orders else 0,
            "avgBudget": round(sum(budgets) / len(budgets), 1) if budgets else None,
            "topCombos": top}


METRIC_ADVICE = {
    "calorie_overload": "主餐拆半、饮料换 0 卡；对照商品图鉴重建一份配额内组合",
    "calorie_over": "下一餐减量回补；酱料与饮料是最好压缩的两项",
    "sodium_over": "酱料减配或换小份；查看商品图鉴里钠密度更低的替代品",
}


def postmortems(orders):
    out = []
    for o in sorted(orders, key=lambda x: x["datetime"], reverse=True):
        c = o["httpStatus"]
        if c in POSTMORTEM:
            pm = POSTMORTEM[c]
            out.append({
                "id": f"INC-{o['datetime'].replace('-','').replace(':','').replace(' ','-')[:13]}",
                "time": o["datetime"], "sev": SEV.get(c, "P3"), "code": c,
                "kind": "code", "metric": None,
                "label": o["codeLabel"], "store": o.get("store", ""),
                "cause": pm["cause"], "advice": pm["advice"],
                "impact": f"{o['kcal'] if o.get('kcal') is not None else '?'} kcal / "
                          f"{o['sodium'] if o.get('sodium') is not None else '?'} mg 钠 · ¥{o.get('amount','?')}",
            })
        # 指标型事故：营养负荷超标（状态码不受影响，独立立案）
        for b in o.get("breaches", []):
            ma = METRIC_ALERTS[b]
            out.append({
                "id": f"INC-{o['datetime'].replace('-','').replace(':','').replace(' ','-')[:13]}-{b}",
                "time": o["datetime"], "sev": ma["sev"], "code": None,
                "kind": "metric", "metric": b,
                "label": ma["short"], "store": o.get("store", ""),
                "cause": f"指标告警：{ma['desc']}（实测 {o['kcal'] if o.get('kcal') is not None else '?'} kcal / 钠 {o['sodium'] if o.get('sodium') is not None else '?'} mg）",
                "advice": METRIC_ADVICE[b],
                "impact": f"{o['kcal'] if o.get('kcal') is not None else '?'} kcal / "
                          f"{o['sodium'] if o.get('sodium') is not None else '?'} mg 钠 · ¥{o.get('amount','?')}",
            })
    out.sort(key=lambda x: x["time"], reverse=True)
    return out


def sre_level(uptime, err_rate, loop):
    score = round(uptime * 0.7 + max(0, 100 - err_rate) * 0.2
                  + min(loop, 20) / 20 * 100 * 0.1, 1)
    for th, name, desc in LEVELS:
        if score >= th:
            higher = [t for t, *_ in LEVELS if t > th]
            return {"score": score, "level": name, "desc": desc,
                    "next": min(higher) if higher else None}
    return {}


# ── probe 探活循环（v3.0 核心）─────────────────────────────────────
def in_window(now, w):
    ws = now.replace(hour=w["start"][0], minute=w["start"][1], second=0, microsecond=0)
    we = now.replace(hour=w["end"][0], minute=w["end"][1], second=0, microsecond=0)
    return ws, we, ws <= now <= we


def pick_coffee(nutrition):
    """营养表里选一杯确定性咖啡：含咖啡关键词中热量最低者。"""
    cands = [(r["productName"], int(r["energyKcal"]))
             for r in nutrition if any(k in r["productName"] for k in CAFFEINE_KEYWORDS)]
    return min(cands, key=lambda x: x[1]) if cands else ("鲜煮咖啡", None)


def pick_snack(nutrition, gap):
    """缺口内选高蛋白确定性下午茶：kcal≤缺口中蛋白质/热量比最高者。"""
    cands = []
    for r in nutrition:
        kcal, protein = int(r["energyKcal"]), float(r["protein"] or 0)
        if 0 < kcal <= gap and protein >= 8:
            cands.append((r["productName"], kcal, protein, protein / kcal))
    cands.sort(key=lambda x: -x[3])
    return cands[0][:3] if cands else None


def probe_loop(orders, meta, prefs, ops_prev, nutrition):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    todays = [o for o in orders if o["date"] == today]
    caf_today = any(any(k in i["name"] for i in o["items"] for k in CAFFEINE_KEYWORDS)
                    for o in todays)
    intake_today = sum(o["kcal"] or 0 for o in todays)

    probes = []
    prev = ops_prev.get("probes", [])

    # 闭环判定：上一轮 open 探活 → 后续订单采纳 / 窗口关闭判超时
    for pr in prev:
        if pr["status"] != "open":
            continue
        w = PROBE_WINDOWS.get(pr["window"])
        if not w:
            continue
        _, we, _ = in_window(now, w)
        adopted = any(o["datetime"] > pr["at"] and
                      any(k in i["name"] for i in o["items"]
                          for k in (CAFFEINE_KEYWORDS if pr["domain"] == "caffeine" else [""]))
                      for o in orders if pr["domain"] == "caffeine")
        if pr["domain"] == "metabolic":
            adopted = any(o["datetime"] > pr["at"] for o in orders if o["date"] == today)
        if adopted:
            pr["status"] = "adopted"
            pr["closedAt"] = now.strftime("%Y-%m-%d %H:%M:%S")
        elif now > we:
            pr["status"] = "timed_out"
            pr["closedAt"] = now.strftime("%Y-%m-%d %H:%M:%S")
        probes.append(pr)

    recent_timeouts = sum(1 for p in prev if p.get("status") == "timed_out")
    last_y408 = any(o["httpStatus"] == "408" and o["date"] < today
                    for o in orders[-3:])

    for key, w in PROBE_WINDOWS.items():
        ws, we, active = in_window(now, w)
        sig = f"{today}:{key}"

        # 已有同窗口探活记录则不重复下发
        if any(p.get("sig") == sig for p in probes):
            continue

        if key == "morning_coffee":
            if last_y408 and now < ws + timedelta(hours=1):
                probes.append(_probe(sig, key, "425", now, "caffeine",
                                     "昨夜存在 408 深夜摄入，晨间咖啡窗顺延 1 小时，此刻打扰为时过早"))
            elif active and not caf_today:
                name, kcal = pick_coffee(nutrition)
                probes.append(_probe(sig, key, "103", now, "caffeine",
                                     f"打工人醒脑场景：建议来一杯 {name}"
                                     + (f"（{kcal} kcal）" if kcal else "") + "，保持上午清醒"))
            elif now > we and not caf_today:
                probes.append(_probe(sig, key, "599", now, "caffeine",
                                     "晨间咖啡窗关闭前始终未采纳——上午清醒度预算已透支，"
                                     "午后窗口请优先补给"))

        elif key == "afternoon_coffee":
            if active and not caf_today:
                name, kcal = pick_coffee(nutrition)
                probes.append(_probe(sig, key, "103", now, "caffeine",
                                     f"午后清醒场景：建议来一杯 {name}"
                                     + (f"（{kcal} kcal）" if kcal else "") + "，撑过 15:00 的困倦谷"))
            elif now > we and not caf_today:
                probes.append(_probe(sig, key, "599", now, "caffeine",
                                     "午后咖啡窗关闭仍未摄入咖啡因——下午的 CPU 降频已记录在案"))

        elif key == "afternoon_snack" and meta.get("profileSet") and meta.get("goal") in ("cut", "bulk"):
            gap = meta["target"] - intake_today
            if meta["goal"] == "bulk":
                # 增肌：gap = 距盈余目标还差多少；不足则 103 盈余加餐，足够则 204
                if gap <= 0:
                    probes.append(_probe(sig, key, "204", now, "metabolic",
                                         f"今日盈余目标已达成（+{-gap} kcal），增肌窗口主动静默"))
                elif gap >= 250:
                    snack = pick_snack(nutrition, gap)
                    payload = (f"距盈余目标还差 {gap} kcal：建议 {snack[0]}"
                               f"（{snack[1]} kcal / 蛋白 {snack[2]}g）" if snack
                               else f"距盈余目标还差 {gap} kcal：建议蛋白加餐")
                    probes.append(_probe(sig, key, "103", now, "metabolic",
                                         f"增肌场景午后补给窗：{payload}"))
                else:
                    probes.append(_probe(sig, key, "204", now, "metabolic",
                                         f"距盈余目标仅差 {gap} kcal，正餐即可覆盖，主动静默"))
            else:
                if gap < 0:
                    probes.append(_probe(sig, key, "412", now, "metabolic",
                                         f"今日已超减脂预算 {-gap} kcal，下午茶建议被你的目标否决——"
                                         f"这不是失败，是 412 在保护你"))
                elif gap >= 250:
                    snack = pick_snack(nutrition, min(gap, meta["windows"]["snack"] * 2))
                    payload = (f"缺口 {gap} kcal：建议 {snack[0]}（{snack[1]} kcal / 蛋白 {snack[2]}g）"
                               if snack else f"缺口 {gap} kcal：可补给轻量蛋白类加餐")
                    probes.append(_probe(sig, key, "103", now, "metabolic",
                                         f"减脂场景午后补给窗：{payload}，维持下午体力"))
                else:
                    probes.append(_probe(sig, key, "204", now, "metabolic",
                                         f"今日摄入与预算吻合（缺口仅 {gap} kcal），本窗口无需补给，主动静默"))

    # 522：最近连续 2 条探活超时 → 升级失联告警
    tail = [p for p in probes if p["status"] in ("timed_out", "open")][-2:]
    if len(tail) == 2 and all(p["status"] == "timed_out" for p in tail):
        probes.append(_probe(f"{today}:lost", "lost", "522", now, "meta",
                             "连续窗口失联：建议反馈回路中断，下次播报将置顶提醒"))

    return probes


def _probe(sig, window, code, now, domain, detail):
    m = CODE_META[code]
    return {"id": f"PRB-{now.strftime('%Y%m%d%H%M')}-{window}",
            "sig": sig, "window": window, "domain": domain,
            "at": now.strftime("%Y-%m-%d %H:%M:%S"), "code": code,
            "label": m["short"], "color": m["color"], "detail": detail,
            "status": "open"}


def main():
    classified = load("classified.json", None)
    if not classified:
        raise SystemExit("缺少 data/classified.json，先运行 classify.py")
    prefs = load("prefs.json", {"learned": {}, "changelog": []})
    ops_prev = load("ops.json", {"loopCount": 0, "postmortems": [], "probes": [],
                                 "tasteProfile": []})
    nutrition = load("nutrition_foods.json", [])

    orders = classified["orders"]
    s = classified["summary"]
    loop = ops_prev.get("loopCount", 0) + 1
    err_rate = s["errorBudgetUsed"] / s["totalOrders"] * 100 if s["totalOrders"] else 0

    pm_new = postmortems(orders)
    tp_new = taste_profile(orders)
    hab = habits(orders)
    level = sre_level(s["uptime"], err_rate, loop)
    meta = metabolic(prefs)
    probes = probe_loop(orders, meta, prefs, ops_prev, nutrition)

    insights = []
    if hab["nightRate"] >= 20:
        insights.append(f"夜宵率 {hab['nightRate']}%：摄入流量集中在深夜窗口，"
                        f"408 事故大概率由此时段贡献")
    top = hab["topCombos"][:1]
    if top and top[0]["count"] >= 2:
        insights.append(f"「{top[0]['items'][0][:12]}…」组合出现 {top[0]['count']} 次，"
                        f"可设为快捷组合，减少每次决策成本")
    if s.get("itemLedgerGapRate", 0) >= 50:
        insights.append(f"商品级 404 率 {s['itemLedgerGapRate']}%：菜单探索欲远超官方账本收录速度，"
                        f"图鉴页是唯一能完整计量它们的入口")
    if meta.get("profileSet"):
        insights.append(f"代谢档案生效：BMR {meta['bmr']} / TDEE {meta['tdee']} / "
                        f"{meta['goal']} 场景目标 {meta['target']} kcal，探活按此口径判定")
    else:
        insights.append(meta["hint"])
    timeouts = [p for p in probes if p["status"] == "timed_out"]
    if timeouts:
        insights.append(f"已有 {len(timeouts)} 条探活建议窗口超时（599）："
                        f"采纳率是运维闭环的核心指标")
    for t in prefs.get("tastes", []):
        insights.append(f"已加载用户声明偏好：{t}（判定时作为硬约束）")

    prefs.setdefault("learned", {}).update({
        "topCombos": hab["topCombos"], "nightOwl": hab["nightRate"],
        "avgBudget": hab["avgBudget"], "tasteProfile": tp_new,
    })
    changelog = prefs.setdefault("changelog", [])
    changelog.append({"at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "loop": loop,
                      "event": f"第 {loop} 次进化：{len(pm_new)} 份事故复盘 · "
                               f"{len(probes)} 条探活 · {len(insights)} 条洞察 · "
                               f"职级「{level['level']}」"})
    (BASE / "data" / "prefs.json").write_text(
        json.dumps(prefs, ensure_ascii=False, indent=1), encoding="utf-8")

    ops = {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "loopCount": loop, "level": level,
        "postmortems": pm_new,
        "newIncidents": [p["id"] for p in pm_new
                         if p["id"] not in {x["id"] for x in ops_prev.get("postmortems", [])}],
        "tasteProfile": tp_new,
        "newTastes": [t["label"] for t in tp_new
                      if t["label"] not in {x["label"] for x in ops_prev.get("tasteProfile", [])}],
        "habits": hab,
        "metabolic": meta,
        "probes": probes,
        "probesOpen": [p for p in probes if p["status"] == "open"],
        "insights": insights,
        "prefsLoaded": {k: prefs.get(k) for k in ("goals", "tastes", "notes", "profile")},
        "evolutionLog": changelog[-8:],
        "goals": prefs.get("goals", {}),
    }
    (BASE / "data" / "ops.json").write_text(
        json.dumps(ops, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"第 {loop} 次交接班完成 · 职级：{level['level']}（综合 {level['score']}）")
    print(f"事故复盘 {len(pm_new)} 份 · 探活 {len(probes)} 条"
          f"（待处理 {len(ops['probesOpen'])}）· 洞察 {len(insights)} 条")
    if meta.get("profileSet"):
        print(f"代谢：BMR {meta['bmr']} / TDEE {meta['tdee']} / 目标 {meta['target']} kcal")
    open_probes = ops["probesOpen"]
    for pr in open_probes:
        print(f"  [{pr['label']}] {pr['detail']}")
    print("已写入 data/ops.json，prefs.json learned 区已更新")


if __name__ == "__main__":
    main()
