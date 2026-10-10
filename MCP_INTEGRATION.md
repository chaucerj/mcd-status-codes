# MCP_INTEGRATION · 麦当劳 MCP 接入说明

## 使用的 MCP Server

- **服务地址**：`https://mcp.mcd.cn`（麦当劳中国官方）
- **传输协议**：Streamable HTTP
- **认证方式**：`Authorization: Bearer <MCD_MCP_TOKEN>`（Token 经 open.mcd.cn/mcp 控制台激活获得，仅通过环境变量注入，仓库不含任何真实凭证）
- **接入配置**：见 [mcp-config.example.json](mcp-config.example.json)
- **实测工具总数**：35 个

## 实际使用的 Tools

### 只读采集（数据采集阶段）

| Tool | 用途 | 调用时机 |
|---|---|---|
| `order-list` | 拉取历史订单（订单时间、渠道、状态、商品行、金额） | 分类器的主输入 |
| `list-nutrition-foods` | 获取 160 项标准单品营养数据（能量/蛋白质/脂肪/碳水/钠/钙） | 与订单商品做品名匹配 |
| `query-my-account` | 积分账户概览（仅面板展示） | 可选 |

### 下单链路（唯一写操作，默认只试算）

| Tool | 用途 | 安全约束 |
|---|---|---|
| `query-nearby-stores` | 查询可点餐门店（`beType=1` 到店自取） | 只读 |
| `query-meals` | 查询门店菜单，获取 `productCode` | 只读 |
| `calculate-price` | 计算价格，返回 `price`（单位：分）与 `takeWayList` | 只读，**试算终点** |
| `create-order` | 创建订单 | **付费写操作**，仅在显式 `--confirm` 时调用 |

**未使用**任何其他写操作工具：未调用 `auto-bind-coupons`、`draw-lottery`、
`mall-create-order`、`party-order-create`、`cancel-order`、`delivery-create-address`。

## 调用流程

```
collect.py（只读）
  ├─ initialize（Streamable HTTP 握手，Bearer Token 鉴权）
  ├─ tools/call: order-list            → data/orders.parsed.json
  ├─ tools/call: list-nutrition-foods   → data/nutrition_foods.json（160 项）
  └─ tools/call: query-my-account       → data/account.parsed.json

classify.py（本地，不访问 MCP）
  └─ 品名归一化匹配 → 12 级确定性判定阶梯 → data/classified.json

report.py（本地，不访问 MCP）
  └─ 渲染单文件 dashboard.html

order.py（可选，唯一写操作）
  ├─ query-nearby-stores   门店列表
  ├─ query-meals           商品编码
  ├─ calculate-price       试算金额 + 取餐方式   ← 默认止步于此
  └─ create-order          真正下单            ← 仅 --confirm 时执行
```

## 关键实测发现（驱动设计决策）

1. **`order-list` 仅返回最近约 10 单**：监控面板样本口径如实标注"近期订单"，不做长期宣称。

2. **营养表覆盖缺口 = 21.4% 覆盖率**：`list-nutrition-foods` 仅返回 160 项标准单品
   （自定义分隔符文本格式，形如 `[160]{productName,energyKcal,...}`），
   订单中的联名款/套餐/季节限定无法按品名匹配。实测 14 件商品中仅 3 件可定位。
   该缺口被转化为**独立指标「营养账本覆盖率」**（而非状态码），缺陷转特性。

3. **订单字段满足全部判定需求**：`createTime` 精确到秒（支撑 408 深夜与 429 单日多单判定）、
   `orderStatus` 为中文状态串（含「取消」时判 504）、`orderType` 区分渠道（301）。

4. **MCP 返回体带字段说明头**：真实 JSON 位于 `## Original Response` 段之后，
   且**尾部会追加展示提示文本**。`collect.py` / `order.py` 用 `raw_decode()` 剥离，
   避免 `json.loads()` 因尾部残留文本报错。

5. **门店非营业时段返回 `code=600057`**：实测凌晨 01:17 多数门店返回
   「门店可能已关闭或不在营业时间」。`order.py` 据此优雅降级——不重试、不伪造成功。

6. **24 小时营业门店存在**：青岛门店 `3350181` 在凌晨仍可正常查询菜单与试算，
   可用于验证 404 → 200 闭环。

7. **价格单位为分**：`calculate-price` 返回 `price=3700` 表示 ¥37.00，展示层需换算。

8. **取餐方式码来自试算结果**：`takeWayList[].code` 取值如 `eat-in`（堂食）/
   `take-in-store`（外带），`create-order` 需原样传入。

## 业务价值

把冷冰冰的营养数据和订单流水，翻译成程序员社区的共同语言（状态码/SLO/Uptime/错误预算），
让"回顾自己吃了什么"这件事从一次性年度报告，变成每天可用的持续监控——
同时诚实暴露官方营养表的覆盖边界，为理解"我吃的到底是什么"提供真实参照。

## 安全边界

| 措施 | 说明 |
|---|---|
| 默认只读 | `collect.py` / `classify.py` / `report.py` 全程不产生写操作 |
| 下单需显式确认 | `order.py` 默认止于 `calculate-price`，须传 `--confirm` 才调用 `create-order` |
| 金额显式展示 | 下单前打印门店 / 商品 / 原价 / 优惠 / 取餐方式 |
| 降级不伪造 | 门店打烊（`code=600057`）时直接报错，不假装成功 |
| 凭证不落盘 | Token 仅从环境变量读取，`data/` 已 gitignore，配置仅含占位符 |

## 限流与合规

- 服务限流 600 次/分钟，本工具采集阶段仅 3–4 次调用，远低于阈值
- 仅限个人非商业用途，遵守《麦当劳 MCP 服务规则》
- Token 与订单数据均不落盘到仓库（`data/` 已 gitignore，配置仅环境变量占位符）