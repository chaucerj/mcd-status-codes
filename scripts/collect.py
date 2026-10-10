#!/usr/bin/env python3
"""从麦当劳 MCP 采集只读数据：时间 / 历史订单 / 营养表 / 积分账户。

用法:
  export MCD_MCP_TOKEN=xxx
  python3 scripts/collect.py

产物:
  data/orders.parsed.json       历史订单（原始结构）
  data/nutrition_foods.json     营养表（160 项标准单品）
  data/account.parsed.json      积分账户
只读调用，不领券、不下单、不抽奖。
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mcp_probe import McpClient


def unwrap(resp: dict) -> dict:
    """MCP 返回体带字段说明头，提取 '## Original Response' 之后的原始 JSON。"""
    text = "".join(x.get("text", "") for x in resp.get("result", {}).get("content", []))
    m = text.rfind("## Original Response")
    js = text[m + len("## Original Response"):] if m != -1 else text
    return json.loads(js[js.index("{"):])


def parse_nutrition_table(data: str) -> list:
    """营养表为自定义文本格式: [160]{cols}:\n  名称,null,kj,kcal,..."""
    m = re.match(r"\[(\d+)\]\{([^}]+)\}:\n(.*)", data, re.S)
    if not m:
        raise SystemExit("营养表格式无法解析，官方接口可能已变更")
    cols, body = m.group(2).split(","), m.group(3)
    rows = []
    for line in body.splitlines():
        parts = [p.strip() for p in line.strip().split(",")]
        if len(parts) == len(cols):
            rows.append(dict(zip(cols, parts)))
    return rows


def main():
    token = os.environ.get("MCD_MCP_TOKEN")
    if not token:
        raise SystemExit("export MCD_MCP_TOKEN=<token>（open.mcd.cn/mcp 控制台激活）")
    base = Path(__file__).resolve().parent.parent
    (base / "data").mkdir(exist_ok=True)

    c = McpClient(token)
    c.initialize()

    _, resp = c.rpc("tools/call", {"name": "order-list", "arguments": {}})
    orders = unwrap(resp)
    (base / "data" / "orders.parsed.json").write_text(
        json.dumps(orders, ensure_ascii=False, indent=1), encoding="utf-8")
    n = len(orders["data"]["list"])
    print(f"✓ order-list：{n} 单已保存")

    _, resp = c.rpc("tools/call", {"name": "list-nutrition-foods", "arguments": {}})
    raw = unwrap(resp)
    rows = parse_nutrition_table(raw["data"])
    (base / "data" / "nutrition_foods.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ list-nutrition-foods：{len(rows)} 项营养数据已保存")

    _, resp = c.rpc("tools/call", {"name": "query-my-account", "arguments": {}})
    (base / "data" / "account.parsed.json").write_text(
        json.dumps(unwrap(resp), ensure_ascii=False, indent=1), encoding="utf-8")
    print("✓ query-my-account：积分账户已保存")


if __name__ == "__main__":
    main()
