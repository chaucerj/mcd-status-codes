---
name: mcd-status-codes
description: 麦门监控台 —— 主动运维型身体 SRE。把每一笔麦当劳订单判定为 HTTP 状态码（双方向语义宪法 v4.0：18 码 + 3 指标告警），Agent 依据代谢模型（体重/身高/年龄→BMR→TDEE→分餐预算）在咖啡窗与补给窗主动探活提醒：该喝没喝的咖啡判 599 超时、减脂缺口下发 103 下午茶建议、超预算 412 否决、异常订单自动生成 P1-P3 事故复盘。当用户想回顾麦当劳订单、查看热量/营养/健康合规、生成监控面板或状态码报告、听取主动补给提醒、复盘事故或查询自己的 SRE 职级，或询问 1024 程序员节限定玩法时使用。基于麦当劳中国官方 MCP 只读采集，全部数值确定性可复算。
license: MIT
---

# 麦门监控台 · 身体服务运维 Skill（值班手册）

**语义宪法（最高优先级，任何输出都不得违反）—— v4.0 双方向声明制 + 语义分层**

> **你是主体，你的身体是服务端。**

- **ingest 摄入方向**（你发起）：每一笔订单 = 一次摄入请求，状态码 = 你的身体对这批摄入的生命周期响应（12 码）。营养负荷（热量/钠）是**指标告警**不是状态码（v4.0）：超配额记入 breaches 触发 P1/P2 事故复盘，不占码
- **probe 探活方向**（你的运维 Agent 发起）：Agent 依据代谢模型主动探活，状态码 = 这次探活的结果（6 码：103/204/412/425/599/522）

铁律：

1. ingest 类状态码定义句的主语只能是「你 / 你的身体 / 你的摄入行为」；probe 类主语只能是「你的运维 Agent」，被探对象仍然是你
2. 麦当劳官方数据、MCP 接口、营养表等平台侧事实**只能作为诊断证据**出现，绝不充当状态码定义
3. 一个状态码只有**一个含义、一个方向**，全项目逐字一致
4. **语义的唯一事实源是 `scripts/codes.py`**，完整 18 码定义表与指标告警见 [references/state-codes.md](references/state-codes.md)，冲突时以 codes.py 为准

## 前置条件

- MCP Token：open.mcd.cn/mcp 登录激活，环境变量 `MCD_MCP_TOKEN`
- Python 3.10+，纯标准库零第三方依赖
- 所有命令在**本仓库根目录**执行（本仓库即 Skill 目录）

## 值班流程（每次会话按此顺序执行）

### 第 0 步：交接班播报（主动提醒，先于回答用户问题）

读 `data/ops.json`（若存在）：

- `probesOpen` 队列非空 → **主动播报**每条待处理探活（播报模板见 [references/agent-playbook.md](references/agent-playbook.md)）
- `level` 与上次相比有晋升 → 先报喜
- `newIncidents` 非空 → 播报新事故
- 用户回复「采纳 / 忽略」→ 将对应 probe 的 `status` 改为 `adopted / ignored`（下次 evolve.py 自动判定超时为 timed_out）

### 第 1 步：采集数据（只读）

```bash
python3 scripts/collect.py
```

调用 order-list / query-order（商品图）/ list-nutrition-foods / query-my-account。**禁止调用任何领券、抽奖工具；下单走第 5 步守则。**

### 第 2 步：分类 + 自进化 + 面板

```bash
python3 scripts/classify.py    # ingest 判定（确定性规则，数值不进 LLM）
python3 scripts/evolve.py      # 交接班：事故复盘/口味画像/代谢探活/职级
python3 scripts/report.py      # 单文件 dashboard.html
```

无 Token 演示：`python3 scripts/make_demo.py && python3 scripts/classify.py demo/demo_orders.json && python3 scripts/report.py`

### 第 3 步：代谢档案代笔（用户提供数值时）

用户口述体重/身高/年龄/性别/活动量/场景（减脂 cut、增肌 bulk、保持 keep、打工人醒脑 worker）→ 写入 `data/prefs.json` 的 `profile` 区。**该文件已被 .gitignore，敏感数据绝不入库**。声明偏好（忌口/目标上限）写 goals/tastes 区；`learned` 区由 evolve.py 自动维护，勿手改。

### 第 4 步：探活闭环维护

- 窗口规则与探活码触发条件见 [references/state-codes.md](references/state-codes.md) 探活窗口一节
- 用户问「下午该不该吃点东西」→ 运行 evolve.py 取最新探活判定（103/204/412），**不要心算热量缺口**

### 第 5 步：下单（唯一写操作，默认只试算）

`scripts/order.py` 默认只调 calculate-price 试算；**仅当用户明确确认后**才加 `--confirm` 调用 create-order。绝不自动下单。

## 回答用户查询的规范

- **数字必须来自 `data/classified.json` / `data/ops.json`**，禁止心算或编造；营养表匹配不到的餐品如实报 404，不猜测营养值
- 播报口径：先职级/晋升 → 待处理探活 → 新事故 → 新洞察；语气可带运维梗，但数字永远严肃
- 医疗相关追问：输出仅为娱乐性数据复盘，不构成营养或医疗建议
- 用户问「我运维得怎么样」→ 汇报职级、Uptime、闭环质量（采纳率）与事故趋势

## 1024 彩蛋

10/20–10/26 自动进入 1024 模式（`report.py --1024` 可强制）：1024 kcal = 1G，年度摄入换算流量单位；10/24 当天提醒用户生成限定卡片分享。
