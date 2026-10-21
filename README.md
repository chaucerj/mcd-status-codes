# 麦门监控台 · 主动运维型身体 SRE

<img src="docs/logo.png" width="64" alt="Golden Arches" />

*（Logo 取自大赛官方仓库 [M-China/mcd-developer-innovation-challenge](https://github.com/M-China/mcd-developer-innovation-challenge) 活动横幅，版权归麦当劳所有）*

> **你是一自己身体服务的 on-call 工程师。**
> 每一笔麦当劳订单 = 一次摄入请求，你的身体返回一个 HTTP 状态码；
> Agent 依据你的代谢模型主动探活——催你喝咖啡、帮你拦下午茶、
> 给异常订单写事故复盘、按 Uptime 给你晋升 SRE 职级。
> 1024 程序员节 × 麦当劳官方 MCP 参赛作品。

<p align="center">
  <a href="https://chaucerj.github.io/mcd-status-codes/"><b>🎮 在线试玩间（免Token、零安装，对话点餐+时间轴探活+晒卡）→</b></a>
</p>

<p align="center">
  <a href="https://github.com/chaucerj/mcd-status-codes/stargazers?style=social"><img src="https://img.shields.io/github/stars/chaucerj/mcd-status-codes?style=social" alt="Star"></a>
  <a href="https://github.com/M-China/mcd-developer-innovation-challenge/issues/264"><img src="https://img.shields.io/badge/%E5%B7%B2%E8%BF%87%E5%AE%A1-1024%E7%A8%8B%E5%BA%8F%E5%91%98%E8%8A%82-ffc700?style=social" alt="已过审"></a>
  <a href="https://github.com/chaucerj/mcd-status-codes"><img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT"></a>
  <a href="https://github.com/chaucerj/mcd-status-codes"><img src="https://img.shields.io/badge/%E4%BE%9D%E8%B5%96-0-brightgreen" alt="零依赖"></a>
</p>

| 项目信息 | 内容 |
|---|---|
| **赛事** | 麦当劳中国程序员节创意开发大赛（[活动仓库](https://github.com/M-China/mcd-developer-innovation-challenge)） |
| **形态** | Agent Skill + 对话式点餐 + 确定性分类器 + 单文件 Grafana 监控面板 |
| **数据来源** | 麦当劳中国官方 MCP（`https://mcp.mcd.cn`），只读采集 |
| **运行环境** | Python 3.10+，纯标准库，零第三方依赖 |
| **在线试玩** | [chaucerj.github.io/mcd-status-codes](https://chaucerj.github.io/mcd-status-codes/) —— 免 Token、零安装，对话点餐 + 时间轴探活 + 晒卡导出 |
| **语义版本** | v4.0（RULES_VERSION，事实源 [`scripts/codes.py`](scripts/codes.py)） |

![监控台](docs/screenshot-normal.png)

## 三级页面

| 页面 | 深链 | 定位 |
|---|---|---|
| **监控台** | 默认 / `#day` `#week` | Uptime 仪表、摄入时间轴、状态码构成、热量分位、监控告警、SLA 分级、请求日志（含官方商品图缩略图） |
| **商品图鉴** | `#gallery` | 跨单聚合的图形化营养账本——官方商品图、热量条、钠合计、出现轨迹 |
| **运维战情室** | `#ops` | **重生之我在麦门世界运维**——事故复盘 / 口味画像 / 代谢模型 / 探活队列 / SRE 职级 / 自进化日志 |

**场景定位选择**：监控台「定位视图」面板支持均衡 / 减脂 / 增肌 / 打工人四种定位一键切换，每种定位有专属指标卡与针对性策略，定位同时驱动探活窗口行为。

![商品图鉴](docs/screenshot-gallery.png)

![运维战情室](docs/screenshot-ops.png)

## 对话式点餐（Agent 主动运维的核心交互）

打开试玩间就是一段与**值班运维 Agent** 的对话：

```
👤 20块吃什么
🤖 按你的要求组了一单（3 件，合计 792 kcal）：巨无霸 + 中薯条 + 无糖可乐
   [✅ 就这样下单] [🔁 换一换] [☰ 我自己逛菜单]

👤 减脂能吃啥
🤖 减脂补给窗：缺口 1800 kcal——建议薄皮焦香V翅（192 kcal / 蛋白 14g）
   [✅ 采纳：立即摄入]
```

Agent 是**确定性规则引擎**（关键词意图解析 + 约束贪心组单），不联网、不猜数。

**时间轴**（00:00–23:59 滑块）= 时间旅行：拖到不同时刻，Agent 按代谢窗口探活——

| 拖到 | 会发生什么 |
|---|---|
| 10:00 不点咖啡 | ☕ 103 Hints：「建议一杯小杯鲜萃咖啡（15 kcal）」 |
| 拖过 11:00 还不喝 | 🔴 599 Coffee Timeout：清醒度预算透支 |
| 15:00 一天没吃 | 🥗 103 补给窗：缺口 1800 kcal，下发下午茶 |
| 15:00 已吃 2000 kcal | 🟠 412 Precondition Failed：下午茶被目标否决 |
| 15:40 只差 150 kcal | 🟢 204 No Content：主动静默 |
| 23:59 提交 | 🌙 408 Request Timeout（深夜窗口） |

**采纳即闭环**：点「✅ 采纳」，建议转为下单，状态码实时返回，探活标记 closed——因果连贯。

![1024 限定模式](docs/screenshot-1024.png)

## DIY 新品工坊 + 新品心愿榜

**两款官方还没有的玩法**（全大赛 832 投稿无人做过）：

- **🧪 DIY 新品工坊**：全场 107 项官方餐品任意搭配，不设基底——薯条蘸甜筒、鸡块配鳕鱼堡，都行。**创意组合优先，营养不参与评审**。合成入库判 201 Created · 自制新品。
- **📮 新品心愿榜**：说一句官方菜单里没有的东西（「麻辣香锅味鸡腿堡」）→ Agent 判 404 后引导入榜，**愿力 +1**。愿力榜 = 「最想让官方做出来」的民意排行，生成晒卡去拉票。

对 Agent 说「🧪 DIY 新品」或「📮 新品心愿榜」即可进入。

## Agent 自进化循环

每次运行 `python3 scripts/evolve.py` 就是一次「交接班」：事故复盘、口味画像、职级、洞察全部由**确定性规则**重新计算（数值不进 LLM、逐条可复算），学习结果沉淀进 `data/prefs.json`——越用越懂你。Agent（WorkBuddy / Claude 等）负责编排循环、播报变化、把你口述的偏好（忌口 / 目标 / 预算）写进档案。

## 语义宪法 v4.0

这是本项目唯一且不可妥协的视角约定。

> **你是主体，你的身体是服务端。**

**v3.0 双方向声明制**——状态码必须归属以下两个方向之一：

| 方向 | 发起方 | 含义 | 码数 |
|---|---|---|---|
| **ingest** 摄入方向 | 你发起 | 你的身体对每次摄入的响应 | 12 码 |
| **probe** 探活方向 | 运维 Agent 发起 | Agent 主动探活/补给建议的结果 | 6 码 |

**v4.0 语义分层**——营养负荷（热量/钠）是**指标（metrics）**不是状态码。真实 HTTP 里负载大小是 Content-Length 头部而非状态码；"吃了一顿大的"不是服务器错误。超配额走**指标告警**，事故复盘照常立案，但不占用任何状态码。

**为什么这条如此重要**：早期版本的 404 一会儿指"官方营养表查不到"（平台视角），一会儿指"身体账本记不下"（自身视角），语义漂移导致读者无法判断指标到底在说什么。现在语义的**唯一事实源是 [`scripts/codes.py`](scripts/codes.py)**，语义漂移在工程上被根除了。

## 为什么做这个

麦当劳 App 里能看到订单列表，但看不到**趋势**：这个月比上月吃得多还是少？断供了几天？连点两次的那天到底发生了什么？这些问题的答案需要一个监控面板，而不是一个流水账。

我们把它做成程序员一眼就能读懂的形态——因为状态码、Uptime、错误预算是我们每天在盯的东西。

真实账户上跑出的三组数据：

- **Uptime 10.1%**：89 天里只有 9 天有订单记录。你的用餐可用性，可能还没有你负责的那个服务高。
- **429 限流真实存在**：某天连点两单，第二单被判定为请求过频。
- **商品级营养账本缺口 78.6%**：官方营养表只收录 160 项标准单品，联名款/套餐/季节限定在官方数据里全部 404——这不是 bug，是你的菜单探索欲远超官方收录速度。

## 安装

零第三方依赖，Python 3.10+ 即可。

```bash
git clone https://github.com/chaucerj/mcd-status-codes.git
cd mcd-status-codes
```

### 作为 Agent Skill 导入

本仓库即 Skill 目录（`SKILL.md` 在根目录，符合 Agent Skill 规范）。克隆后在 WorkBuddy / Claude / Cursor 等客户端中将仓库目录作为 Skill 加载，Agent 会按 `SKILL.md` 的值班手册工作：**会话开始先播报待处理探活**，再按需采集/分类/进化/出面板。`references/` 下有两份速查：`state-codes.md`（18 码语义全表 + 指标告警）与 `agent-playbook.md`（Agent 播报手册）。

配置 MCP Token（在 [open.mcd.cn/mcp](https://open.mcd.cn/mcp) 登录 → 控制台 → 激活获取）：

```bash
export MCD_MCP_TOKEN=你的Token
```

## 使用

```bash
# 1. 采集（只读：历史订单 + 商品图 + 营养表 + 积分账户）
python3 scripts/collect.py

# 2. 分类（确定性规则引擎，可复算）
python3 scripts/classify.py

# 3. 自进化交接班（事故复盘 / 口味画像 / 职级 / 探活）
python3 scripts/evolve.py

# 4. 生成监控面板（单文件 HTML，双击打开）
python3 scripts/report.py

# 1024 程序员节限定模式（10/20–10/26 自动激活，也可手动开启）
python3 scripts/report.py --1024
```

没有 Token？用合成演示数据体验完整流程：

```bash
python3 scripts/make_demo.py
python3 scripts/classify.py demo/demo_orders.json
python3 scripts/evolve.py
python3 scripts/report.py
```

## 状态码定义表

> 本表与 [`scripts/codes.py`](scripts/codes.py) 逐字一致，由它生成。

### ingest 摄入方向（12 码）

判定阶梯从最"贵"的失败到常规成功，首个命中即停。

| 状态码 | 你的身体发生了什么 | 确定性触发条件 |
|---|---|---|
| **504 Gateway Timeout** | 上游中止—— 这次摄入最终没有发生，链路在上游超时中止 | 订单状态为已取消 |
| **429 Too Many Requests** | 摄入请求过频—— 你在同一天发起了多次摄入，身体对你限流 | 当日第 2 单及以后 |
| **408 Request Timeout** | 请求超时—— 你在深夜发起摄入请求，但身体已不在服务时段 | 下单时间落在 22:00–04:59 |
| **418 I'm a teapot** | 我是茶壶—— 你只点了非咖啡因饮料，请求打到了茶壶而不是咖啡机 | 整单商品均为非咖啡因饮品 |
| **502 Bad Gateway** | 聚合网关—— 这次请求聚合了多个子请求，单次摄入量过大 | 单笔商品总件数 ≥ 6 |
| **304 Not Modified** | 缓存命中—— 这次摄入与上一单完全一致，身体直接复用了上次的响应 | 商品组合与份数同上一单逐项相同 |
| **301 Moved Permanently** | 取餐渠道永久改道—— 你的取餐路径换了节点，并已永久指向新渠道 | 本次取餐方式与上一单不同 |
| **404 Not Found** | 账本缺口—— 这次摄入的商品在官方营养账本里查不到 | 全部商品均不在营养表中 |
| **201 Created** | 新资源入库—— 你吃到了历史上从未出现过的单品，身体新建了一条记录 | 该品名在此前全部订单中均未出现过 |
| **206 Partial Content** | 摄入无法完整计量—— 你的身体账本里查不全这次摄入，返回的是残缺甚至空的响应 | 部分（0/N 至 N-1/N）商品无法在营养账本中定位 |
| **200 OK** | 摄入已入账—— 你的身体正常受理了这次摄入，并完成记账 | 全部商品热量可计算 |

### probe 探活方向（6 码，v3.0 新增）

| 状态码 | 含义 | 触发 |
|---|---|---|
| **103 Early Hints** | 补给建议下发—— Agent 依据你的代谢曲线提前给出提示 | 探活窗口开启且存在缺口 |
| **204 No Content** | 主动静默—— 本窗口无需补给，Agent 正确地保持了沉默 | 当日摄入与预算吻合 |
| **412 Precondition Failed** | 建议被目标否决—— 建议与你声明的目标冲突 | 超出 goals 上限 |
| **425 Too Early** | 过早打扰—— Agent 判定此刻探活为时过早 | 前一晚存在 408 深夜摄入 |
| **599 Network Timeout** | 建议窗口超时—— 补给建议直到窗口关闭都未被采纳 | 窗口期内无对应摄入 |
| **522 Connection Timed Out** | 连续窗口失联—— 探活建议始终未获反馈，告警升级 | 连续 2 个窗口无反馈 |

### 集合层状态码

| 状态码 | 含义 | 触发 |
|---|---|---|
| **404 Not Found** | **订单不存在**—— 你的身体服务上还没有任何订单资源 | 初始拉取时订单集合为空 |
| **503 Service Unavailable** | **身体服务宕机**—— 这一天你的身体服务完全没有响应 | 当日零订单，计入 Uptime 分母 |

### 指标告警层（v4.0）

营养负荷（热量/钠）是**指标（metrics）**不是状态码——超配额记入 breaches 触发事故复盘，不改变订单的状态码。

| 告警 | 阈值 | 级别 |
|---|---|---|
| 热量超配额 | 单餐 > 800 kcal | P2 |
| 热量过载 | 单餐 > 1500 kcal | P1 |
| 钠超标 | 单餐 > 1200 mg | P2 |

### 两个关键设计决定

**1. 404 只保留一个触发条件，且能变成 200**

404 **不再**有"商品查不到营养表"这层含义。它只表示一件事：**你的身体服务上还没有任何订单资源**。对零订单用户，首次运行会直接渲染一张 404 彩蛋页——资源不存在，而**这个「不存在」本身就是结论**。

**2. 「营养账本缺口」从状态码降级为独立指标**

官方营养表只收录 160 项标准单品，联名款/套餐无法按品名匹配。若把它塞进 404 会造成语义污染。所以它现在是面板上的**独立指标「营养账本覆盖率」**，与状态码体系正交。

## 监控面板输出

Grafana 暗色科技风，单文件 HTML 零依赖。图表全部为**手绘 SVG**，不引任何图表库。

**三组交互，状态彼此独立、互不干扰**：

| 交互 | 位置 | 说明 |
|---|---|---|
| 统计维度 | 时间轴右上 | 按天 / 按周，切换后全指标按新维度重算 |
| 状态码筛选 | 日志标题右侧 | chips 形式，点击只看某一类响应码 |
| 日志分页 | 日志右下 | 每页 5 单，焦点在日志区内可用 ← → 翻页 |

| # | 组件 | 说明 |
|---|---|---|
| 1 | **Uptime 环形仪表** | 20 格刻度环+ 渐变弧，弧长即结论 |
| 2 | **摄入请求时间轴** | 按当前维度分桶，柱高=摄入次数，色=当期最严重状态码 |
| 3 | **状态码构成** | 横向堆叠条，色块内嵌百分比 |
| 4 | **单餐热量标尺** | 分段渐变量程 + 阈值刻度线，P50/P99 指针落位 |
| 5 | **累计摄入流量** | 1 kcal = 1 Byte，1024 进制换算 |
| 6 | **监控告警 + 错误预算 + SLA 分级** | 金/银/铜/Best Effort 四档 |
| 7 | **营养账本缺口清单** | 无法计量的商品 Top 8（副指标） |
| 8 | **请求日志** | 分页 + 状态码筛选 + 官方商品图缩略图 |
| 9 | **1024 限定区** | 摄入总量换算为流量单位 |

无障碍：所有交互元素均带 `role` / `aria-*` 属性、`:focus-visible` 焦点环；颜色不作为唯一信息载体。

## 目标用户

- **程序员/互联网从业者**：看得懂状态码，也想看看自己的用餐数据大盘长什么样
- **想复盘饮食习惯的人**：比"年度账单"多一层持续监控视角——趋势、断供、复发都有指标可看
- **喜欢 DIY 和创意的人**：发明官方没有的新品、给它起名、看它被判什么状态码——纯粹的创造乐趣
- **麦当劳会员**：想知道"我吃的这些到底多少热量"——顺带发现官方营养表的覆盖缺口

## 隐私与边界

- 所有数据留在本机 `data/` 目录（已 gitignore），Token 只从环境变量读取
- 代谢档案（体重/身高/年龄）存本地 `prefs.json`，不入仓库
- 采集全程只读；唯一的写操作是 `order.py`，且**默认只试算**，需显式 `--confirm` 才会下单
- 不领券、不抽奖、不改账户
- 输出为娱乐性数据复盘，不构成营养或医疗建议；餐品信息以麦当劳官方渠道实时结果为准

## 参赛说明

本作品为麦当劳程序员节创意开发大赛参赛项目，基于麦当劳中国官方 MCP（`https://mcp.mcd.cn`）开发，独立开发、非官方产品。MCP 接入说明见 [MCP_INTEGRATION.md](MCP_INTEGRATION.md)。

---

<h2 id="star" align="center">喜欢这份大盘的话，帮我点一下 ⭐</h2>

<p align="center">
  <a href="https://github.com/chaucerj/mcd-status-codes/stargazers"><img src="https://img.shields.io/github/stars/chaucerj/mcd-status-codes?style=for-the-badge&labelColor=ffc700" alt="Star"></a>
  <a href="https://github.com/chaucerj/mcd-status-codes/network/members"><img src="https://img.shields.io/github/forks/chaucerj/mcd-status-codes?style=for-the-badge&labelColor=8A2BE2" alt="Fork"></a>
  <a href="https://github.com/chaucerj/mcd-status-codes/watchers"><img src="https://img.shields.io/github/watchers/chaucerj/mcd-status-codes?style=for-the-badge&labelColor=555" alt="Watch"></a>
</p>

这是我在麦当劳程序员节创意开发大赛的参赛作品，**正在按 Star 数排名中**。

如果你也想看自己的麦当劳账户长什么样——

- **点 ⭐ Star**：这是对我最直接的认可，也是让作品被更多人看到的唯一方式
- **点 🍴 Fork**：拿去改成你自己的版本，用你自己的订单数据跑一遍
- **点 👀 Watch**：后续迭代（更多状态码、更多维度）我会在这里通知

**不用注册任何东西、不需要 Token、点一下就好。** 三秒钟。

<p align="center">
  <a href="https://github.com/chaucerj/mcd-status-codes"><b>⭐ Star 这个仓库</b></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/chaucerj/mcd-status-codes/issues/264"><b>查看参赛 Issue</b></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/M-China/mcd-developer-innovation-challenge"><b>查看官方活动仓库</b></a>
</p>
