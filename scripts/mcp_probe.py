#!/usr/bin/env python3
"""Minimal MCP Streamable HTTP probe for McDonald's mcp.mcd.cn (stdlib only).

Usage:
  export MCD_MCP_TOKEN=your_token
  python3 scripts/mcp_probe.py                      # initialize + tools/list
  python3 scripts/mcp_probe.py query-my-account '{}'  # call a tool
"""
import json
import os
import sys
import uuid
import urllib.request
import urllib.error

BASE = "https://mcp.mcd.cn"


class McpClient:
    def __init__(self, token: str, base: str = BASE):
        self.base = base
        self.session_id = None
        self.id_counter = 0
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

    def _post(self, payload: dict, timeout: int = 60):
        headers = dict(self.headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        req = urllib.request.Request(
            self.base, data=json.dumps(payload).encode("utf-8"),
            headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                # capture session id from any casing of the header
                for key, value in resp.headers.items():
                    if key.lower() == "mcp-session-id":
                        self.session_id = value
                ctype = resp.headers.get("Content-Type", "")
                body = resp.read().decode("utf-8", errors="replace")
                status = resp.status
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"HTTP {e.code}: {body[:500]}")
        if "text/event-stream" in ctype:
            data = None
            for line in body.splitlines():
                if line.startswith("data:"):
                    data = line[5:].strip()
            return status, (json.loads(data) if data else None)
        return status, (json.loads(body) if body.strip() else None)

    def rpc(self, method: str, params: dict | None = None):
        self.id_counter += 1
        payload = {"jsonrpc": "2.0", "id": self.id_counter, "method": method}
        if params is not None:
            payload["params"] = params
        return self._post(payload)

    def initialize(self):
        _, resp = self.rpc("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "mcd-status-codes-probe", "version": "0.1"},
        })
        print("== initialize ==")
        print(json.dumps(resp, ensure_ascii=False, indent=2)[:600])
        # notifications carry no id and return 202 empty
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        print(f"session: {self.session_id}\n")

    def list_tools(self):
        _, resp = self.rpc("tools/list", {})
        tools = (resp or {}).get("result", {}).get("tools", [])
        print(f"== tools/list: {len(tools)} tools ==")
        for t in tools:
            desc = (t.get("description") or "").split("\n")[0][:60]
            print(f"- {t.get('name')}  {desc}")
        return tools

    def call(self, name: str, arguments: dict):
        _, resp = self.rpc("tools/call", {"name": name, "arguments": arguments})
        print(f"== tools/call {name} ==")
        print(json.dumps(resp, ensure_ascii=False, indent=2)[:4000])


def main():
    token = os.environ.get("MCD_MCP_TOKEN")
    if not token:
        raise SystemExit("export MCD_MCP_TOKEN=<your token> first (open.mcd.cn/mcp -> console -> activate)")
    client = McpClient(token)
    client.initialize()
    if len(sys.argv) >= 2:
        args = json.loads(sys.argv[2]) if len(sys.argv) >= 3 else {}
        client.call(sys.argv[1], args)
    else:
        client.list_tools()


if __name__ == "__main__":
    main()
