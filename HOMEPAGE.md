# 麦门状态码 · 你的身体 API 监控台

把每一笔麦当劳订单判定为一个 HTTP 状态码，生成 Grafana 暗色科技风的监控面板。

**一句话**：程序员每天对着一堆状态码，却没人给自己的身体发过状态码。

- **参赛活动**：麦当劳程序员节创意开发大赛（1024 程序员节）
- **技术形态**：Agent Skill（SKILL.md）+ 本地 Python 确定性分类器 + 单文件 HTML 监控面板
- **数据来源**：麦当劳中国官方 MCP（`https://mcp.mcd.cn`），只读采集
- **运行环境**：Python 3.10+，纯标准库，零第三方依赖

## 快速开始

```bash
export MCD_MCP_TOKEN=<你的 Token>   # open.mcd.cn/mcp 控制台激活获取
python3 scripts/collect.py    # 采集（只读）
python3 scripts/classify.py   # 分类（确定性规则）
python3 scripts/report.py     # 生成 dashboard.html
```

没有 Token？用合成演示数据体验完整流程：

```bash
python3 scripts/make_demo.py
python3 scripts/classify.py demo/demo_orders.json
python3 scripts/report.py
```

## 核心特色

| 特性 | 说明 |
|---|---|
| **语义宪法** | 唯一视角「你是主体，你的身体是服务端」，状态码只描述你的身体对摄入的响应 |
| **单一事实源** | `scripts/codes.py` 定义与诊断证据物理隔离，从工程上杜绝语义漂移 |
| **维度切换** | 统计维度可按天/按周切换，Uptime 分母、状态码构成、错误预算全量重算 |
| **手绘 SVG 图表** | 环形仪表、分桶时间轴、堆叠条、分位标尺、SLA 分级，不引任何图表库 |
| **404 → 200 闭环** | 零订单用户从 404 起步，下单后资源被创建，集合层状态码当场跳变 |
| **安全边界** | 采集全程只读；下单默认仅试算，须显式 `--confirm` 才产生付费写操作 |

## 仓库导航

- [README.md](README.md) —— 项目介绍、安装、使用示例、目标用户
- [SKILL.md](SKILL.md) —— Agent Skill 定义（含语义宪法与状态码表）
- [MCP_INTEGRATION.md](MCP_INTEGRATION.md) —— MCP Server、Tool、调用流程与业务价值
- [CONTEST_DECLARATION.md](CONTEST_DECLARATION.md) —— 参赛声明（官方原样保留）
- [DESIGN.md](DESIGN.md) —— 设计稿（定位、语义架构、发布节奏）
- [workbuddy.md](workbuddy.md) —— WorkBuddy 开发对话上下文
- `scripts/` —— 主程序（纯标准库，零第三方依赖）
- `tools/` —— 开发者辅助脚本（截图等，不参与主流程）
- `docs/` —— 面板截图与 Logo

## 隐私与合规

- 所有数据留在本机 `data/` 目录（已 gitignore），Token 仅从环境变量读取
- 配置文件仅含环境变量占位符，仓库不含任何真实凭证
- 输出为娱乐性数据复盘，不构成营养或医疗建议

---

本作品为麦当劳程序员节创意开发大赛参赛项目，基于麦当劳中国官方 MCP 开发，
**独立开发、非官方产品**。餐品信息、价格及供应状态以麦当劳官方渠道实时结果为准。