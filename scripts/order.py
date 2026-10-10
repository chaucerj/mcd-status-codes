#!/usr/bin/env python3
"""麦门监控台 · 下单脚本：让你的身体服务从 404 变为 200。

这条链路由MCP 官方文档给出的固定顺序组成：
    query-nearby-stores → query-meals → calculate-price → create-order

安全设计（重要）：
  · **默认只试算，不下单**。仅传 `--confirm` 才会真正调用 create-order。
  · create-order 是**付费写操作**，会产生真实订单与费用。
    脚本在下单前打印门店、商品、金额，必须由人确认后再继续。
  · 门店打烊时（code=600057）不重试、不降级伪造，明确报错并提示换时段。

用法:
  export MCD_MCP_TOKEN=xxx
  python3 scripts/order.py                      # 列出收藏门店 + 巨无霸价格（只读试算）
  python3 scripts/order.py --store 1450433       # 指定门店试算
  python3 scripts/order.py --store 1450433 --confirm   # 真正下单（付费！）
  python3 scripts/order.py --item巨无霸 --qty 1  # 自定义商品
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mcp_probe import McpClient

DEFAULT_ITEM = "巨无霸"


def unwrap(resp: dict) -> tuple:
    """MCP 返回体带字段说明头 + 尾部追加展示提示，用 raw_decode 只取原始 JSON。

    返回 (payload, error_message)。payload 为 None 表示业务失败。
    """
    text = "".join(x.get("text", "") for x in resp.get("result", {}).get("content", []))
    i = text.rfind("## Original Response")
    js = text[i + len("## Original Response"):] if i != -1 else text
    j = js.find("{")
    if j < 0:
        return None, text.strip()[:300]
    try:
        payload, _ = json.JSONDecoder().raw_decode(js[j:])
    except json.JSONDecodeError:
        return None, js[j:j + 300]
    if not payload.get("success", False):
        return None, f"code={payload.get('code')} {payload.get('message', '')}"
    return payload, None


def call(c: McpClient, name: str, args: dict) -> tuple:
    _, resp = c.rpc("tools/call", {"name": name, "arguments": args})
    return unwrap(resp)


def list_stores(c: McpClient, be_type: int = 1) -> list:
    """收藏门店列表。beType=1 到店自取（无 beCode）。"""
    d, err = call(c, "query-nearby-stores", {"searchType": 1, "beType": be_type})
    if err:
        print(f"! 门店查询失败：{err}")
        return []
    return d.get("data") or []


def find_items(c: McpClient, store_code: str, keyword: str) -> list:
    """在门店菜单中按关键词找商品，返回 [{code,name,price}]。"""
    d, err = call(c, "query-meals", {"storeCode": store_code, "orderType": 1, "beType": 1})
    if err:
        return [{"_error": err}]
    out = []
    data = d.get("data") or {}
    meals_map = data.get("meals") or {}
    for cat in data.get("categories") or []:
        for m in cat.get("meals") or []:
            code = m.get("code")
            detail = meals_map.get(code) or {}
            name = detail.get("name") or m.get("name") or ""
            if keyword in name:
                out.append({
                    "code": code,
                    "name": name,
                    "price": detail.get("currentPrice") or m.get("price"),
                    "category": cat.get("name") or "",
                })
    return out


def main():
    ap = argparse.ArgumentParser(description="麦门状态码 · 下单（默认只试算）")
    ap.add_argument("--store", help="门店编码 storeCode，不传则列出收藏门店")
    ap.add_argument("--item", default=DEFAULT_ITEM, help=f"商品关键词，默认 {DEFAULT_ITEM}")
    ap.add_argument("--qty", type=int, default=1, help="数量，默认 1")
    ap.add_argument("--confirm", action="store_true",
                    help="真正下单（付费写操作！不加此参数仅试算）")
    args = ap.parse_args()

    token = os.environ.get("MCD_MCP_TOKEN")
    if not token:
        raise SystemExit("export MCD_MCP_TOKEN=<token>（open.mcd.cn/mcp 控制台激活）")

    c = McpClient(token)
    c.initialize()

    # ── 1. 确定门店 ────────────────────────────────────────────────────
    if args.store:
        store_code, be_type, be_code = args.store, 1, None
        print(f"→ 使用指定门店 {store_code}")
    else:
        stores = list_stores(c)
        if not stores:
            print("！未获取到可用门店（可能无收藏记录或接口异常），"
                  "可用 --store <storeCode> 指定。")
            return
        print("你的收藏门店（到店自取beType=1）：")
        for s in stores[:10]:
            print(f"  {s.get('storeCode'):<10} {s.get('storeName')}· {str(s.get('address'))[:28]}")
        store_code = stores[0].get("storeCode")
        print(f"\n→ 默认使用第一家：{store_code}（加 --store可切换）")

    # ── 2. 查商品 ──────────────────────────────────────────────────────
    print(f"\n→ 在菜单中查找「{args.item}」…")
    items = find_items(c, store_code, args.item)
    if not items:
        print(f"！菜单中未找到「{args.item}」，或门店已打烊（code=600057）。")
        print("  提示：凌晨时段多数门店不在营业时间，可稍后重试或换门店。")
        return
    if items[0].get("_error"):
        print(f"！菜单查询失败：{items[0]['_error']}")
        print("  常见原因：门店已关闭或不在营业时间（MCP 返回 code=600057）。")
        return

    for it in items[:8]:
        print(f"  {it['code']:<14} {it['name']:<22} ¥{it['price']}")
    target = items[0]
    items_arg = [{"productCode": target["code"], "quantity": args.qty}]

    # ── 3. 试算价格 ────────────────────────────────────────────────────
    price_args = {"storeCode": store_code, "orderType": 1, "beType": 1, "items": items_arg}
    d, err = call(c, "calculate-price", price_args)
    if err:
        print(f"！价格试算失败：{err}")
        print("  门店可能已打烊，或商品不可售。下单已中止。")
        return
    data = d.get("data") or {}
    # 金额单位为分（实测 price=3700 → ¥37.00）
    cents = data.get("price") or data.get("productPrice") or data.get("payAmount")
    total = f"¥{cents / 100:.2f}" if isinstance(cents, (int, float)) else "—"
    take_ways = data.get("takeWayList") or []
    take_way = take_ways[0].get("code") if take_ways else None

    print("\n══════ 试算结果 ══════")
    print(f"门店：{store_code}")
    print(f"商品：{target['name']} × {args.qty}")
    print(f"金额：{total}（原价 ¥{(data.get('originalPrice') or 0) / 100:.2f}，"
          f"优惠 ¥{(data.get('discount') or 0) / 100:.2f}）")
    print(f"取餐方式：{'、'.join(f'{t.get('title')}({t.get('code')})' for t in take_ways) or '—'}")

    # ── 4. 下单（需显式确认）──────────────────────────────────────────
    if not args.confirm:
        print("\n（未下单）这是试算模式。确认无误后加 --confirm 参数才会真正下单（会产生费用）。")
        return

    if not take_way:
        print("！未取到 takeWayCode，无法下单。")
        return
    print("\n⚠️  即将创建真实订单并产生费用…")
    order_args = {
        "storeCode": store_code, "orderType": 1, "beType": 1,
        "takeWayCode": take_way, "items": items_arg,
    }
    d, err = call(c, "create-order", order_args)
    if err:
        print(f"下单失败：{err}")
        return
    order_id = (d.get("data") or {}).get("orderId") or (d.get("data") or {}).get("orderNo")
    print(f"✓ 下单成功！订单号 {order_id}")
    print("重新运行 collect.py + classify.py，这一单的状态码即为你的身体服务对它的真实响应。")


if __name__ == "__main__":
    main()