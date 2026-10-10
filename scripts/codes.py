#!/usr/bin/env python3
"""麦门状态码 · 语义单一事实源（Single Source of Truth）

═══════════════════════════════════════════════════════════════════════════
【语义宪法】唯一视角：你是主体，你的身体是服务端。

每一笔订单 = 一次摄入请求 → 打向「你的身体」这台服务实例。
状态码 = **你的身体**对这批摄入的响应。

铁律（违反即视为语义 bug）：
  1. 每个状态码的定义句，主语只能是「你 / 你的身体 / 你的摄入行为」。
  2. 麦当劳官方数据、MCP 接口、营养表等平台侧事实，
     只能出现在「诊断证据」里（reason / evidence），绝不能充当状态码的定义。
  3. 一个状态码只有**一个**含义，全项目（SKILL.md / README / DESIGN.md /
     dashboard / classify.py）必须逐字一致。

═══════════════════════════════════════════════════════════════════════════
"""
import re

RULES_VERSION = "2.0"

# ── Grafana 官方调色板（面板与本文件共用，保证视觉与语义同源）────────────
GF = {
    "blue": "#3274D9", "green": "#37872D", "orange": "#E98300",
    "red": "#E24D42", "purple": "#705DA0", "yellow": "#EAB839",
    "cyan": "#6ED0E0", "darkred": "#96222A",
}

# ── 判定阈值（全部确定性，数值不进 LLM）────────────────────────────────
KCAL_OK = 800       # ≤800 kcal 且钠达标 → 200
KCAL_OVERLOAD = 1500  # >1500 kcal → 500
SODIUM_DENIED = 1200  # >1200mg → 403
NIGHT_START, NIGHT_END = 22, 5  # 22:00–04:59 → 408
BIG_ORDER_QTY = 6   # 单笔总件数 ≥6 → 502
STREAK_ALERT = 3    # 连续 304 达此数触发告警

DRINK_KEYWORDS = [
    "可乐", "雪碧", "芬达", "美汁源", "咖啡", "拿铁", "摩卡", "美式",
    "奶茶", "果汁", "柠檬水", "果茶", "椰汁", "椰饮", "豆浆", "牛奶",
    "矿泉水", "纯水", "冰爽茶", "热巧", "奶昔", "气泡水",
]

# 非食用商品（联名周边等）：身体没有可摄入实体 → 404 的第一触发路径
NON_FOOD_KEYWORDS = [
    "帽", "玩具", "周边", "纪念", "卡包", "卡套", "帆布", "T恤", "卫衣",
    "马克杯", "水杯", "保温", "钥匙扣", "徽章", "贴纸", "盲盒", "手办",
    "书包", "雨伞", "玩偶", "摆件", "杯垫",
]

# ════════════════════════════════════════════════════════════════════════
# 状态码字典
#   meaning —— 唯一定义句，主语必须是「你/你的身体」，不得出现平台侧主语
#   evidence —— 平台侧事实，仅作诊断证据展示，不参与定义
#   class    —— 面板配色语义：ok / warn / error / info
# ════════════════════════════════════════════════════════════════════════
CODE_META = {
    "200": {
        "name": "200 OK", "short": "200 OK", "class": "ok", "color": GF["green"],
        "title": "摄入已入账",
        "meaning": "你的身体正常受理了这次摄入，并完成记账",
        "evidence": "全部商品热量可计算，且在单餐配额内",
    },
    "201": {
        "name": "201 Created", "short": "201 Created", "class": "ok", "color": GF["green"],
        "title": "新资源入库",
        "meaning": "你吃到了历史上从未出现过的单品，身体新建了一条记录",
        "evidence": "该品名在此前全部订单中均未出现过",
    },
    "206": {
        "name": "206 Partial Content", "short": "206 Partial", "class": "info", "color": GF["cyan"],
        "title": "摄入无法完整计量",
        "meaning": "你的身体账本里查不全这次摄入，返回的是残缺甚至空的响应",
        "evidence": "部分（0/N 至 N-1/N）商品无法在营养账本中定位",
    },
    "301": {
        "name": "301 Moved Permanently", "short": "301 Moved", "class": "info", "color": GF["purple"],
        "title": "取餐渠道永久改道",
        "meaning": "你的取餐路径换了节点，并已永久指向新渠道",
        "evidence": "本次取餐方式与上一单不同",
    },
    "304": {
        "name": "304 Not Modified", "short": "304 Not Modified", "class": "info", "color": GF["cyan"],
        "title": "缓存命中",
        "meaning": "这次摄入与上一单完全一致，身体直接复用了上次的响应",
        "evidence": "商品组合与份数同上一单逐项相同",
    },
    "403": {
        "name": "403 Forbidden", "short": "403 Forbidden", "class": "error", "color": GF["red"],
        "title": "营养署拒绝放行",
        "meaning": "你的热量或钠超出单餐配额，身体的准入网关拦下了这单",
        "evidence": "超出单餐 800 kcal 或 1200 mg 钠阈值",
    },
    "404": {
        "name": "404 Not Found", "short": "404 Not Found", "class": "error", "color": GF["red"],
        "title": "订单不存在",
        "meaning": "你的身体服务上还没有任何订单资源，这一单查无此物",
        "evidence": "初始拉取时订单集合为空，或该订单从未存在",
        "scope": "collection",
    },
    "408": {
        "name": "408 Request Timeout", "short": "408 Timeout", "class": "warn", "color": GF["orange"],
        "title": "请求超时",
        "meaning": "你在深夜发起摄入请求，但身体已不在服务时段",
        "evidence": "下单时间落在 22:00–04:59",
    },
    "418": {
        "name": "418 I'm a teapot", "short": "418 teapot", "class": "info", "color": GF["purple"],
        "title": "我是茶壶",
        "meaning": "你只点了饮料，请求打到了茶壶而不是餐桌",
        "evidence": "整单商品均为饮品",
    },
    "429": {
        "name": "429 Too Many Requests", "short": "429 Too Many", "class": "warn", "color": GF["orange"],
        "title": "摄入请求过频",
        "meaning": "你在同一天发起了多次摄入，身体对你限流",
        "evidence": "当日第 2 单及以后",
    },
    "500": {
        "name": "500 Internal Server Error", "short": "500 Server Error", "class": "error", "color": GF["darkred"],
        "title": "系统过载",
        "meaning": "单餐热量超出身体的处理能力，服务当场过载",
        "evidence": "单餐热量 > 1500 kcal",
    },
    "502": {
        "name": "502 Bad Gateway", "short": "502 Bad Gateway", "class": "info", "color": GF["purple"],
        "title": "聚合网关",
        "meaning": "这一次请求聚合了多个子请求，单次摄入量过大",
        "evidence": "单笔商品总件数 ≥ 6",
    },
    "503": {
        "name": "503 Service Unavailable", "short": "503 Unavailable", "class": "error", "color": GF["red"],
        "title": "身体服务宕机",
        "meaning": "这一天你的身体服务完全没有响应",
        "evidence": "当日零订单，计入 Uptime 分母",
    },
    "504": {
        "name": "504 Gateway Timeout", "short": "504 Timeout", "class": "error", "color": GF["darkred"],
        "title": "上游中止",
        "meaning": "这次摄入最终没有发生，链路在上游超时中止",
        "evidence": "订单状态为已取消",
    },
}

# 判定阶梯（首个命中即停）——从最严重的失败到常规成功
LADDER = [
    "504", "429", "408", "418", "500", "403", "502", "304", "301", "201", "206", "200",
]

# 集合层状态码：不产生于单笔订单，只作用于整个订单集合
#   404 —— 订单集合为空（零订单用户），触发彩蛋
#   503 —— 区间内出现零订单日，计入 Uptime 分母
ACCOUNT_CODES = {"404", "503"}

# 零订单彩蛋文案（404 专属）
EASTER_EGG_404 = {
    "title": "404 Not Found · 你的身体服务上还没有任何订单资源",
    "lines": [
        "本次拉取返回空集合 —— 你的身体服务处于**从未被调用**状态。",
        "这在 REST 语义里是最标准的一种 404：资源不存在，且这个「不存在」本身就是结论。",
        "别慌，这不是故障。把任意一单麦当劳下进来，资源即被创建，状态码会立刻跳到 200。",
    ],
    "cta": "执行 `python3 scripts/order.py` 下你的第一单巨无霸套餐，即可让资源从 404 变为 200。",
}


def normalize(name: str) -> str:
    """归一化品名：去空格、去【】品牌段、去数量前后缀。"""
    s = re.sub(r"\s+", "", name)
    s = re.sub(r"【[^】]*】", "", s)
    s = re.sub(r"^\d+\s*(份|个|杯|包|块)", "", s)
    s = re.sub(r"\d+\s*份$", "", s)
    return s


def is_drink(name: str) -> bool:
    return any(k in name for k in DRINK_KEYWORDS)


def is_non_food(name: str) -> bool:
    """判断是否非食用商品（联名周边等）。"""
    return any(k in name for k in NON_FOOD_KEYWORDS)


def label(code: str) -> str:
    return CODE_META[code]["name"]


def short(code: str) -> str:
    return CODE_META[code]["short"]