#!/usr/bin/env python3
"""生成 Grafana 暗色科技风的单文件监控面板 dashboard.html（零依赖，双击打开）。

用法: python3 scripts/report.py [--1024]
  --1024  强制进入 1024 程序员节限定模式（默认仅 10/20–10/26 自动激活）

语义唯一来源：scripts/codes.py —— 面板不自行定义任何状态码含义。
"""
import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from codes import CODE_META, KCAL_OK, KCAL_OVERLOAD, RULES_VERSION

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>麦门监控台 · 你的身体服务</title>
<style>
  :root {{
    --bg:#0b0c0e; --panel:#111217; --panel2:#181b1f; --border:#24272e;
    --text:#d8d9da; --muted:#8e9095; --dim:#6c7076;
    --blue:#3274D9; --green:#37872D; --orange:#E98300;
    --red:#E24D42; --purple:#705DA0; --yellow:#EAB839; --cyan:#6ED0E0;
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:var(--bg);color:var(--text);
    font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:20px;max-width:1240px;margin:0 auto}}
  .mono{{font-family:"SF Mono","JetBrains Mono",Consolas,monospace;
    font-variant-numeric:tabular-nums}}

  .topbar{{display:flex;align-items:center;gap:14px;padding-bottom:12px;
    border-bottom:1px solid var(--border);margin-bottom:16px;flex-wrap:wrap}}
  .topbar img{{width:28px;height:28px;border-radius:3px}}
  .topbar h1{{font-size:17px;font-weight:600;letter-spacing:.2px}}
  .topbar h1 .accent{{color:var(--blue)}}
  .crumb{{font-size:12px;color:var(--dim)}}
  .badge{{margin-left:auto;padding:3px 11px;border-radius:2px;font-size:11px;
    border:1px solid var(--border);color:var(--muted);background:var(--panel)}}
  .badge.on{{background:var(--yellow);border-color:var(--yellow);color:#111;font-weight:700}}

  .meta{{font-size:11px;color:var(--dim);margin-bottom:16px;letter-spacing:.3px;line-height:1.7}}

  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-bottom:10px}}
  .grid4{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin-bottom:10px}}
  .panel{{background:var(--panel);border:1px solid var(--border);border-radius:3px;padding:13px 15px}}
  .panel-h{{display:flex;align-items:center;gap:7px;margin-bottom:9px}}
  .panel-h h3{{font-size:11px;color:var(--muted);font-weight:600;letter-spacing:.7px;text-transform:uppercase}}
  .dot{{width:7px;height:7px;border-radius:50%;flex:none}}

  .stat{{font-size:30px;font-weight:700;line-height:1.15;letter-spacing:-.5px;
    font-variant-numeric:tabular-nums}}
  .stat small{{font-size:13px;color:var(--muted);font-weight:500}}
  .stat-note{{font-size:11px;color:var(--dim);margin-top:5px;line-height:1.5}}

  .bar{{height:5px;background:var(--panel2);border-radius:3px;overflow:hidden;margin-top:9px}}
  .bar>div{{height:100%;border-radius:3px}}

  .row{{display:flex;align-items:center;gap:9px;padding:4px 0;font-size:12px}}
  .row .lb{{width:132px;flex:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    padding:2px 7px;border-radius:2px;font-size:10px;font-weight:700;text-align:center}}
  .row .barwrap{{flex:1;height:13px;background:var(--panel2);border-radius:2px;overflow:hidden}}
  .row .barwrap>div{{height:100%;min-width:2px}}
  .row .ct{{width:26px;text-align:right;flex:none;color:var(--muted)}}

  .uptime{{display:flex;gap:2px;flex-wrap:wrap;margin-top:8px}}
  .ud{{width:9px;height:16px;border-radius:1px}}

  table{{width:100%;border-collapse:collapse;font-size:12px}}
  th{{text-align:left;color:var(--dim);font-size:10px;font-weight:600;letter-spacing:.6px;
    text-transform:uppercase;padding:7px 8px;border-bottom:1px solid var(--border);white-space:nowrap}}
  td{{padding:8px;border-bottom:1px solid var(--border);vertical-align:top}}
  tbody tr:hover{{background:var(--panel2)}}
  .reason{{color:var(--muted);font-size:11px;margin-top:3px;line-height:1.5}}
  .code{{display:inline-block;padding:2px 8px;border-radius:2px;font-size:10px;font-weight:700;white-space:nowrap}}

  .alert{{display:flex;gap:8px;padding:8px 11px;background:var(--panel2);
    border-left:2px solid var(--orange);border-radius:0 2px 2px 0;margin-bottom:6px;
    font-size:12px;line-height:1.55}}

  details summary{{cursor:pointer;list-style:none;color:var(--muted);font-size:11px}}
  details summary::-webkit-details-marker{{display:none}}
  .item{{font-size:11px;padding:2px 0;color:var(--muted)}}
  .item.miss{{color:var(--red)}}
  .item.miss::after{{content:" 无法计量";font-weight:600}}

  .egg-wrap{{text-align:center;padding:44px 24px}}
  .egg-code{{font-size:64px;font-weight:800;letter-spacing:-2px;color:var(--red);line-height:1}}
  .egg-title{{font-size:17px;font-weight:600;margin:14px 0 18px}}
  .egg-box{{max-width:560px;margin:0 auto;text-align:left;background:var(--panel2);
    border:1px solid var(--border);border-radius:3px;padding:16px 18px;font-size:13px;line-height:1.85}}
  .egg-box p{{margin-bottom:9px}}
  .egg-box p:last-child{{margin-bottom:0}}
  .egg-cta{{margin-top:18px;padding:13px 16px;background:rgba(50,116,217,.1);
    border:1px solid var(--blue);border-radius:3px;font-size:13px;line-height:1.7}}

  .locked{{text-align:center;padding:28px;color:var(--dim);font-size:13px}}
  footer{{margin-top:22px;padding-top:14px;border-top:1px solid var(--border);
    color:var(--dim);font-size:11px;text-align:center;line-height:1.8}}

  /* ── 图表 ────────────────────────────────────────────────── */
  .chart-wrap{{width:100%;overflow:visible}}
  .chart-wrap svg{{display:block;width:100%;height:auto;overflow:visible}}
  .axis-line{{stroke:var(--border);stroke-width:1}}
  .axis-text{{fill:var(--dim);font-size:9px;font-family:"SF Mono",Consolas,monospace}}
  .grid-line{{stroke:var(--border);stroke-width:1;stroke-dasharray:2 3;opacity:.55}}
  .bar{{transition:opacity .15s ease}}
  .bar:hover{{opacity:.75}}
  .legend{{display:flex;flex-wrap:wrap;gap:5px 14px;margin-top:10px;
    padding-top:9px;border-top:1px solid var(--border)}}
  .legend-item{{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--muted)}}
  .legend-item .sw{{width:8px;height:8px;border-radius:2px;flex:none}}
  .legend-item .lv{{font-family:"SF Mono",monospace;color:var(--text);font-weight:600}}
  .legend-item .ln{{color:var(--dim)}}

  /* 仪表盘：容器必须与 SVG 显示尺寸一致（112×112），否则 inset:0 居中的
     环心文字锚在 96 容器的 (48,48)，而圆环实际中心在 (56,56)，读数会偏左上 */
  .gauge-wrap{{display:flex;align-items:center;gap:16px}}
  .gauge{{position:relative;width:112px;height:112px;flex:none}}
  .gauge svg{{display:block;transform:rotate(-90deg)}}
  .gauge .gv{{position:absolute;inset:0;display:flex;flex-direction:column;
    align-items:center;justify-content:center;gap:1px}}
  .gauge .gv b{{font-size:25px;font-weight:700;line-height:1;letter-spacing:-.5px;
    font-family:"SF Mono",Consolas,monospace}}
  .gauge .gv i{{font-size:9px;font-style:normal;color:var(--dim);letter-spacing:.4px}}

  /* 热量标尺 */
  .scale{{position:relative;height:60px;margin-top:6px}}
  .scale-track{{position:absolute;top:24px;left:0;right:0;height:7px;
    background:var(--panel2);border-radius:4px;overflow:hidden;display:flex}}
  .scale-seg{{height:100%}}
  .scale-thr{{position:absolute;top:19px;width:1px;height:17px;
    background:var(--dim);opacity:.7}}
  .scale-mark{{position:absolute;top:12px;width:2px;height:31px;background:var(--text);
    border-radius:1px;transform:translateX(-50%);box-shadow:0 0 0 2px var(--panel)}}
  .scale-mark.p50{{height:21px;top:17px;background:var(--cyan)}}
  .scale-mark.p99{{background:var(--purple)}}
  .scale-ticks{{position:absolute;top:37px;left:0;right:0;display:flex;
    justify-content:space-between;font-size:9px;color:var(--dim);
    font-family:"SF Mono",monospace}}

  /* 时间轴刻度 */
  .tl-label{{font-size:10px;color:var(--dim);font-family:"SF Mono",monospace}}

  /* 分段切换控件 */
  .seg{{display:inline-flex;gap:2px;padding:2px;background:var(--panel2);
    border:1px solid var(--border);border-radius:3px}}
  .seg-btn{{appearance:none;border:0;background:transparent;color:var(--muted);
    font-size:11px;font-family:inherit;padding:3px 11px;border-radius:2px;
    cursor:pointer;transition:all .15s ease;line-height:1.5}}
  .seg-btn:hover{{color:var(--text)}}
  .seg-btn.on{{background:var(--blue);color:#fff;font-weight:600}}
  .seg-btn:focus-visible{{outline:2px solid var(--cyan);outline-offset:1px}}

  .panel-h.row{{display:flex;align-items:center;justify-content:space-between;gap:10px}}
  .panel-h.row > div{{display:flex;align-items:center;gap:7px;min-width:0}}

  /* 分页 */
  .pager{{display:flex;align-items:center;gap:8px;justify-content:flex-end;
    padding-top:11px;margin-top:11px;border-top:1px solid var(--border)}}
  .pager-info{{margin-right:auto;font-size:11px;color:var(--dim)}}
  .pg-btn{{appearance:none;min-width:26px;height:26px;padding:0 7px;
    border:1px solid var(--border);background:var(--panel2);color:var(--muted);
    border-radius:3px;font-size:12px;cursor:pointer;font-family:"SF Mono",monospace;
    transition:all .15s ease;line-height:1}}
  .pg-btn:hover:not(:disabled){{color:var(--text);border-color:var(--dim)}}
  .pg-btn:disabled{{opacity:.35;cursor:not-allowed}}
  .pg-btn.on{{background:var(--blue);border-color:var(--blue);color:#fff;font-weight:700}}
  .pg-btn:focus-visible{{outline:2px solid var(--cyan);outline-offset:1px}}
  .pg-gap{{color:var(--dim);padding:0 2px;font-size:12px}}

  /* 状态码筛选 chips */
  .chips{{display:flex;flex-wrap:wrap;gap:5px}}
  .chip-btn{{appearance:none;display:inline-flex;align-items:center;gap:5px;
    padding:3px 9px;border:1px solid var(--border);background:var(--panel2);
    color:var(--muted);border-radius:11px;font-size:11px;cursor:pointer;
    font-family:inherit;transition:all .15s ease;line-height:1.6}}
  .chip-btn:hover{{color:var(--text)}}
  .chip-btn.on{{background:var(--panel);border-color:var(--dim);color:var(--text)}}
  .chip-btn .sw{{width:7px;height:7px;border-radius:50%;flex:none}}
  .chip-btn .n{{font-family:"SF Mono",monospace;font-size:10px;color:var(--dim)}}
  .chip-btn:focus-visible{{outline:2px solid var(--cyan);outline-offset:1px}}

  /* SLA 分级 */
  .sla{{display:flex;flex-direction:column;gap:1px}}
  .sla-row{{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:11.5px}}
  .sla-dot{{width:7px;height:7px;border-radius:50%;flex:none}}
  .sla-lb{{flex:1;font-weight:500}}
  .sla-v{{font-family:"SF Mono",monospace;font-size:10px;color:var(--dim)}}
  .sla-s{{font-family:"SF Mono",monospace;font-size:10px;width:38px;text-align:right}}
</style>
</head>
<body>
<div id="app"></div>
<script>
const DATA = __DATA__;
const FORCE_1024 = __FORCE_1024__;
const CODES = __CODES__;
const KCAL_OK = __KCAL_OK__;
const KCAL_OVERLOAD = __KCAL_OVERLOAD__;

/* 语义全部来自 codes.py，面板不自行定义含义 */
const COLOR = {{}}, SHORT = {{}}, TITLE = {{}};
for (const [k, v] of Object.entries(CODES)) {{
  COLOR[k] = v.color; SHORT[k] = v.short; TITLE[k] = v.title;
}}

const s = DATA.summary;
const now = new Date();
const on1024 = FORCE_1024 || (now.getMonth() === 9 && now.getDate() >= 20 && now.getDate() <= 26);
const logo = "__LOGO_B64__";
const esc = t => String(t).replace(/[&<>]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}})[c]);

function topbar(cls, text) {{
  return `<div class="topbar">
    <img src="data:image/png;base64,${{logo}}" alt="Golden Arches">
    <h1>麦门监控台 <span class="accent">// 身体服务监控台</span></h1>
    <span class="crumb">datasource: order-list · rules v${{DATA.rulesVersion}}</span>
    <span class="badge${{cls}}">${{text}}</span>
  </div>
  <div class="meta mono">数据采集 ${{DATA.generatedAt}} · 样本口径：麦当劳 MCP order-list 近期订单 · 全部指标确定性可复算 · 语义唯一来源 scripts/codes.py</div>`;
}}

/* ── SVG 图表工厂：手绘，零依赖，配色取自 codes.py ─────────────── */

/** Uptime 环形仪表：刻度环 + 渐变弧，形状本身即结论 */
function gauge(pct, color) {{
  const R = 42, sw = 9, C = 2 * Math.PI * R;
  const on = C * Math.min(100, Math.max(0, pct)) / 100;
  const gid = 'g' + Math.abs(Math.round(pct * 1000));
  // 刻度环：每 10% 一格，25% 处加长
  let ticks = '';
  for (let i = 0; i < 20; i++) {{
    const a = (i / 20) * 2 * Math.PI - Math.PI / 2;
    const long = i % 5 === 0;
    const r1 = 52, r2 = long ? 56 : 54.5;
    ticks += `<line x1="${{(48 + Math.cos(a) * r1).toFixed(2)}}" y1="${{(48 + Math.sin(a) * r1).toFixed(2)}}"
      x2="${{(48 + Math.cos(a) * r2).toFixed(2)}}" y2="${{(48 + Math.sin(a) * r2).toFixed(2)}}"
      stroke="${{i / 20 * 100 <= pct ? color : 'var(--panel2)'}}" stroke-width="1"
      opacity="${{i / 20 * 100 <= pct ? .85 : .5}}"/>`;
  }}
  return `<div class="gauge">
    <svg viewBox="0 0 96 96" width="112" height="112" role="img"
         aria-label="身体服务 Uptime ${{pct}}%">
      <defs>
        <linearGradient id="${{gid}}" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${{color}}"/>
          <stop offset="100%" stop-color="${{color}}" stop-opacity=".55"/>
        </linearGradient>
      </defs>
      <g>${{ticks}}</g>
      <circle cx="48" cy="48" r="${{R}}" fill="none" stroke="var(--panel2)" stroke-width="${{sw}}"/>
      <circle cx="48" cy="48" r="${{R}}" fill="none" stroke="url(#${{gid}})" stroke-width="${{sw}}"
        stroke-linecap="round" stroke-dasharray="${{on}} ${{C - on}}"/>
    </svg>
    <div class="gv"><b style="color:${{color}}">${{pct}}<i style="font-size:12px">%</i></b><i>UPTIME</i></div>
  </div>`;
}}

/* ── 聚合层：按「天 / 周」切换统计维度 ─────────────────────────
   切换维度时，Uptime 分母、缺口清单、错误预算全部按新维度重算，
   避免出现「图变了但数字没变」的自相矛盾。
   周口径：ISO 周（周一为一周之始），末尾不足一周按实际天数计入分母。 */

/** ISO 周键，如 2026-W41 */
function isoWeek(d) {{
  const t = new Date(d + 'T00:00:00');
  const day = (t.getDay() + 6) % 7;              // 周一=0
  t.setDate(t.getDate() - day + 3);              // 移到本周周四（ISO 规则）
  const year = t.getFullYear();
  const jan4 = new Date(year, 0, 4);
  const week = 1 + Math.round(((t - jan4) / 86400000 - 3 + ((jan4.getDay() + 6) % 7)) / 7);
  return {{ key: year + '-W' + String(week).padStart(2, '0'), start: null }};
}}

/** 周维度下每个桶的起始日期（用于 x 轴刻度标签） */
function weekStart(d) {{
  const t = new Date(d + 'T00:00:00');
  const day = (t.getDay() + 6) % 7;
  t.setDate(t.getDate() - day);
  return t.toISOString().slice(0, 10);
}}

const SEV = {{'504':5,'503':4,'500':4,'429':3,'408':3,'403':3,'502':2,'418':2,'206':1,'304':1,'301':1,'201':0,'200':0}};

/** 构造按当前维度聚合后的桶数组 */
function buildBuckets(dim) {{
  const days = s.days || [];
  const orders = DATA.orders || [];
  const byDay = {{}};
  orders.forEach(o => {{ (byDay[o.date] = byDay[o.date] || []).push(o); }});

  if (dim === 'day') {{
    return days.map(d => {{
      const list = byDay[d.date] || [];
      return {{
        key: d.date, label: d.date.slice(5),
        span: 1, ordered: list.length ? 1 : 0,
        count: list.length, orders: list,
        worst: list.length ? list.reduce((a, b) => SEV[b.httpStatus] > SEV[a.httpStatus] ? b : a) : null,
        multi: list.length > 1,
      }};
    }});
  }}

  // 周维度
  const groups = [];
  const index = {{}};
  days.forEach(d => {{
    const w = isoWeek(d.date);
    if (!index[w.key]) {{
      index[w.key] = {{ key: w.key, label: weekStart(d.date).slice(5), start: weekStart(d.date),
        span: 0, ordered: 0, count: 0, orders: [], worst: null, multi: false }};
      groups.push(index[w.key]);
    }}
    const g = index[w.key];
    const list = byDay[d.date] || [];
    g.span += 1;
    if (list.length) g.ordered += 1;
    g.count += list.length;
    list.forEach(o => {{
      g.orders.push(o);
      if (!g.worst || SEV[o.httpStatus] > SEV[g.worst.httpStatus]) g.worst = o;
    }});
    g.multi = g.multi || list.length > 1;
  }});
  return groups;
}}

/** 按维度重算核心指标，保证与图表口径一致
    Uptime 分母 = 该维度的总桶数（天→ 天数，周 → 周数）
    Uptime 分子 = 有摄入的桶数        */
function metrics(dim) {{
  const b = buildBuckets(dim);
  const span = b.length;                              // 桶数：周维度即周数
  const active = b.filter(x => x.count > 0).length;   // 有摄入的桶数
  const dist = {{}};
  const all = dim === 'day'
    ? (DATA.orders || [])
    : b.flatMap(x => x.orders);
  all.forEach(o => {{ dist[o.httpStatus] = (dist[o.httpStatus] || 0) + 1; }});
  const err = Object.entries(dist).reduce((a, [c, n]) =>
    (c.startsWith('4') || c.startsWith('5')) && c !== '206' ? a + n : a, 0);
  return {{ buckets: b, span, active,
    ordered: active,
    uptime: span ? Math.round(active / span * 1000) / 10 : 0,
    dist, total: all.length, err }};
}}

/** 摄入请求时间轴：横轴按当前维度分桶，柱高 = 摄入次数，色 = 最严重状态码 */
function timeline(dim, m) {{
  const b = m.buckets;
  if (!b.length) return '<div class="stat-note">无数据</div>';
  const n = b.length;
  const maxN = Math.max(1, ...b.map(x => x.count));
  const unit = dim === 'day' ? '天' : '周';
  const idle = n - m.active;
  // 用真实像素宽度作为 viewBox，避免 preserveAspectRatio="none" 拉伸文字
  const W = Math.max(600, Math.min(1100, n * (dim === 'day' ? 9 : 46)));
  const px = W / n;                       // 每格像素宽
  const H = 132, padB = 22, padT = 10;
  const plotH = H - padB - padT;

  const refLines2 = [0.5, 1].map(f => {{
    const y = H - padB - plotH * f;
    return `<line class="grid-line" x1="0" y1="${{y}}" x2="${{W}}" y2="${{y}}"
      style="stroke-dasharray:2 4;opacity:.4"/>`;
  }}).join('');

  let bars2 = '';
  b.forEach((g, i) => {{
    const x = i * px;
    if (!g.count) {{
      bars2 += `<rect x="${{x + px * 0.2}}" y="${{H - padB - 2}}" width="${{px * 0.6}}"
        height="2" fill="var(--panel2)"/>
        <rect x="${{x + px * 0.2}}" y="${{H - padB - 5}}" width="${{px * 0.6}}"
          height="1.5" fill="var(--panel2)" opacity=".55">
          <title>${{g.label}} · 503 Service Unavailable · 该${{unit}}零摄入</title></rect>`;
      return;
    }}
    const h = (g.count / maxN) * plotH * 0.72 + 12;
    const col = COLOR[g.worst.httpStatus];
    bars2 += `<rect class="bar" x="${{x + px * 0.16}}" y="${{H - padB - h}}"
      width="${{px * 0.68}}" height="${{h}}" rx="1.5" fill="${{col}}"
      opacity=".92"><title>${{g.label}} · ${{SHORT[g.worst.httpStatus]}} · ${{g.count}} 单 · ${{TITLE[g.worst.httpStatus]}}</title></rect>`;
    if (g.multi) {{
      bars2 += `<circle cx="${{x + px * 0.5}}" cy="${{H - padB - h - 5}}" r="2.4" fill="${{col}}">
        <title>${{g.label}} · 该${{unit}}出现单日多单（429 限流）</title></circle>`;
    }}
  }});

  const ticks2 = [];
  const step2 = Math.max(1, Math.ceil(n / (dim === 'day' ? 4 : 7)));
  b.forEach((g, i) => {{
    if (dim === 'day') {{
      const mth = g.key.slice(5, 7);
      if (i === 0 || mth !== b[i-1].key.slice(5,7)) {{
        ticks2.push(`<line class="grid-line" x1="${{i * px}}" y1="${{padT}}" x2="${{i * px}}" y2="${{H - padB}}" style="opacity:.5"/>`);
        ticks2.push(`<text class="axis-text" x="${{i * px + 3}}" y="${{H - 6}}">${{mth}} 月</text>`);
      }}
    }} else {{
      if (i % step2 !== 0) return;
      const cx = i * px + px / 2;
      ticks2.push(`<line class="grid-line" x1="${{i * px}}" y1="${{padT}}" x2="${{i * px}}" y2="${{H - padB}}" style="opacity:.35"/>`);
      ticks2.push(`<text class="axis-text" x="${{cx}}" y="${{H - 6}}" text-anchor="middle">${{g.label}}</text>`);
    }}
  }});

  return `<div class="chart-wrap">
    <svg viewBox="0 0 ${{W}} ${{H}}" style="width:100%;height:${{H}}px" role="img"
         preserveAspectRatio="xMidYMid meet"
         aria-label="摄入请求时间轴，按${{unit}}聚合，${{m.span}} ${{unit}}中 ${{m.active}} ${{unit}}有响应">
      ${{refLines2}}
      <line class="axis-line" x1="0" y1="${{H - padB}}" x2="${{W}}" y2="${{H - padB}}"/>
      ${{ticks2.join('')}}
      ${{bars2}}
    </svg>
  </div>
  <div class="legend">
    <span class="legend-item"><span class="sw" style="background:var(--panel2)"></span>
      <span class="ln">503 零摄入${{unit}}（${{idle}} ${{unit}}）</span></span>
    <span class="legend-item"><span class="sw" style="background:var(--green)"></span>
      <span class="ln">柱高 = 摄入次数</span></span>
    <span class="legend-item"><span class="sw" style="background:var(--orange)"></span>
      <span class="ln">圆点 = 单日多单</span></span>
  </div>`;
}}

/** 状态码分布：横向堆叠条 + 图例，比一堆并列条更快读出占比 */
function distBar(m) {{
  const dist = Object.entries(m.dist).sort((a, b) => b[1] - a[1]);
  const total = dist.reduce((a, b) => a + b[1], 0) || 1;
  let x = 0;
  const GAP = dist.length > 1 ? 0.6 : 0;   // 段间留缝，窄段不缝
  const segs = dist.map(([c, n]) => {{
    const w = n / total * 100;
    const pct = Math.round(n / total * 100);
    // 数值只走图例行与 tooltip：viewBox 非等比拉伸下段内文字必然变形
    const g = w > GAP * 3 ? GAP / 2 : 0;
    const seg = `<g><rect x="${{(x + g).toFixed(2)}}" y="0" width="${{(w - g * 2).toFixed(2)}}"
      height="100%" fill="${{COLOR[c]}}" rx="2"><title>${{SHORT[c]}} · ${{n}} 次 · ${{pct}}%</title></rect></g>`;
    x += w;
    return seg;
  }}).join('');

  const legend = dist.map(([c, n]) => `
    <span class="legend-item">
      <span class="sw" style="background:${{COLOR[c]}}"></span>
      <span class="lv">${{SHORT[c]}}</span>
      <span class="ln">${{n}} · ${{Math.round(n/total*100)}}%</span>
    </span>`).join('');

  return `<div class="chart-wrap">
    <svg viewBox="0 0 100 8" preserveAspectRatio="none" style="height:9px"
         role="img" aria-label="状态码分布占比">${{segs}}</svg>
  </div>
  <div class="legend">${{legend}}</div>`;
}}

/** 维度切换控件：分段按钮，遵循 radiogroup 语义 */
function dimToggle(cur) {{
  const opts = [['day', '按天'], ['week', '按周']];
  return `<div class="seg" role="radiogroup" aria-label="统计维度">
    ${{opts.map(([v, t]) => `<button class="seg-btn${{cur === v ? ' on' : ''}}"
      role="radio" aria-checked="${{cur === v}}" data-dim="${{v}}"
      type="button">${{t}}</button>`).join('')}}
  </div>`;
}}

/** 热量标尺：分段量程 + 阈值刻度线 + P50/P99 指针 */
function kcalScale() {{
  const MAX = 1500, p50 = s.kcalP50, p99 = s.kcalP99;
  const pos = v => Math.min(100, (v || 0) / MAX * 100);
  return `<div class="scale">
    <div class="scale-track">
      <div class="scale-seg" style="width:${{pos(KCAL_OK)}}%;background:linear-gradient(90deg,rgba(55,135,45,.65),rgba(55,135,45,.35))"></div>
      <div class="scale-seg" style="width:${{pos(KCAL_OVERLOAD)-pos(KCAL_OK)}}%;background:linear-gradient(90deg,rgba(224,131,0,.6),rgba(224,131,0,.32))"></div>
      <div class="scale-seg" style="width:${{100-pos(KCAL_OVERLOAD)}}%;background:linear-gradient(90deg,rgba(226,77,66,.5),rgba(226,77,66,.26))"></div>
    </div>
    <div class="scale-thr" style="left:${{pos(KCAL_OK)}}%" title="403 阈值 ${{KCAL_OK}} kcal"></div>
    <div class="scale-thr" style="left:${{pos(KCAL_OVERLOAD)}}%" title="500 阈值 ${{KCAL_OVERLOAD}} kcal"></div>
    ${{p50 != null ? `<div class="scale-mark p50" style="left:${{pos(p50)}}%" title="P50 中位单餐 ${{p50}} kcal"></div>` : ''}}
    ${{p99 != null ? `<div class="scale-mark p99" style="left:${{pos(p99)}}%" title="P99 ${{p99}} kcal"></div>` : ''}}
    <div class="scale-ticks">
      <span>0</span><span>${{KCAL_OK}}</span><span>${{KCAL_OVERLOAD}}</span>
    </div>
  </div>
  <div class="legend">
    <span class="legend-item"><span class="sw" style="background:rgba(55,135,45,.65)"></span><span class="ln">≤ ${{KCAL_OK}} → 200</span></span>
    <span class="legend-item"><span class="sw" style="background:rgba(224,131,0,.6)"></span><span class="ln">→ 403 营养署拒绝</span></span>
    <span class="legend-item"><span class="sw" style="background:rgba(226,77,66,.5)"></span><span class="ln">>${{KCAL_OVERLOAD}} → 500 过载</span></span>
    ${{p50 != null ? `<span class="legend-item"><span class="sw" style="background:var(--cyan);width:2px;border-radius:0"></span><span class="lv">P50 ${{p50}}</span><span class="ln">kcal 中位单餐</span></span>` : ''}}
    ${{p99 != null ? `<span class="legend-item"><span class="sw" style="background:var(--purple);width:2px;border-radius:0"></span><span class="lv">P99 ${{p99}}</span><span class="ln">kcal</span></span>` : ''}}
  </div>`;
}}

/* ── 集合层 404：订单为空 → 资源不存在，触发彩蛋 ─────────────────── */
function render404() {{
  const egg = s.easterEgg || {{}};
  document.getElementById('app').innerHTML =
    topbar(' on', 'collection 404 · 资源不存在') +
    `<div class="panel"><div class="egg-wrap">
      <div class="egg-code">404</div>
      <div class="egg-title">Not Found · 你的身体服务上还没有任何订单资源</div>
      <div class="egg-box">
        ${{(egg.lines||[]).map(l => `<p>${{l}}</p>`).join('')}}
      </div>
      <div class="egg-cta">${{esc(egg.cta || '')}}</div>
    </div></div>`;
}}

/* ── 正常监控台 ─────────────────────────────────────────────────
   上半屏信息层级（按「监控大屏」而非「数据报表」组织）：
     第一眼  Uptime 环形仪表 —— 本项目最有梗的指标，弧长形状本身即结论
     第二眼  摄入请求时间轴—— 89 天跨度里 9 根柱子，稀疏与空窗一眼可见
     第三眼  状态码构成 / 热量标尺 —— 占比与分位的辅助判读
   图表全部手绘 SVG，保持零第三方依赖；配色取自 codes.py，与语义同源。
   ──────────────────────────────────────────────────────────── */
function render(dim, logFilter, logPage) {{
  dim = dim || 'day';
  LOG_FILTER = logFilter || LOG_FILTER || 'all';
  LOG_PAGE = logPage || 1;
  const cov = s.ledgerCoverageRate || 0;
  const m = metrics(dim);
  const worst = Object.entries(m.dist).sort((a,b)=>(SEV[b[0]]||0)-(SEV[a[0]]||0))[0];
  const worstCode = worst ? worst[0] : null;
  const unit = dim === 'day' ? '天' : '周';
  const idle = m.span - m.ordered;

  // 主视觉：Uptime 仪表 +摄入请求时间轴
  const hero = `
    <div class="panel">
      <div class="panel-h"><span class="dot" style="background:var(--blue)"></span>
        <h3>身体服务可用性</h3></div>
      <div class="gauge-wrap">
        ${{gauge(m.uptime, 'var(--blue)')}}
        <div style="min-width:0">
          <div class="stat-note" style="margin-top:0;font-size:12px">
            近 ${{m.span}} ${{unit}}中仅 <strong style="color:var(--text)">${{m.ordered}}</strong> ${{unit}}有响应<br>
            你的身体服务可用性，可能还没有你负责的那个服务高
          </div>
          <div class="legend" style="border:0;padding:0;margin-top:9px">
            <span class="legend-item"><span class="sw" style="background:var(--panel2)"></span>
              <span class="ln">${{idle}} ${{unit}} 503 宕机</span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-h row">
        <div><span class="dot" style="background:var(--green)"></span>
          <h3>摄入请求时间轴</h3></div>
        ${{dimToggle(dim)}}
      </div>
      ${{timeline(dim, m)}}
    </div>`;

  // 次级：状态码分布 + 热量标尺 + 摄入流量
  const second = `
    <div class="panel">
      <div class="panel-h"><span class="dot" style="background:var(--purple)"></span>
        <h3>状态码构成</h3></div>
      ${{distBar(m)}}
      <div class="stat-note" style="margin-top:11px">
        共 ${{m.total}} 单${{worstCode ? ` · 最严重为 <span style="color:${{COLOR[worstCode]}}">${{SHORT[worstCode]}}</span> (${{TITLE[worstCode]}})` : ''}}
      </div>
    </div>

    <div class="panel">
      <div class="panel-h"><span class="dot" style="background:var(--purple)"></span>
        <h3>单餐热量分位</h3></div>
      ${{kcalScale()}}
    </div>

    <div class="panel">
      <div class="panel-h"><span class="dot" style="background:var(--yellow)"></span>
        <h3>累计摄入流量</h3></div>
      <div class="stat mono" style="color:var(--yellow);font-size:34px">${{s.flowUnit}}</div>
      <div class="stat-note" style="margin-top:7px">
        共 ${{(s.totalKcal||0).toLocaleString()}} kcal · 按 1 kcal = 1 Byte、1024 进制换算<br>
        平均 ${{s.orderedDays ? Math.round(s.totalKcal/s.orderedDays) : 0}} kcal/响应日
      </div>
    </div>`;

  const gapList = (s.missedItems && s.missedItems.length) ? (() => {{
    const mx = Math.max(...s.missedItems.map(x => x[1]));
    return s.missedItems.map(([n,q]) => `
      <div class="row">
        <span class="lb" style="background:var(--panel2);color:var(--muted);font-weight:400">${{esc(n)}}</span>
        <div class="barwrap"><div style="width:${{q/mx*100}}%;background:var(--red);opacity:.6"></div></div>
        <span class="ct mono">×${{q}}</span>
      </div>`).join('');
  }})() : '';

  // ── 请求日志：分页 + 状态码筛选，避免单屏堆叠十余行 ──
  const PER_PAGE = 5;
  const filtered = LOG_FILTER === 'all'
    ? (DATA.orders || [])
    : (DATA.orders || []).filter(o => o.httpStatus === LOG_FILTER);
  const pages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const page = Math.min(LOG_PAGE, pages);
  const slice = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  // 状态码筛选 chips
  const codeCount = {};
  (DATA.orders || []).forEach(o => { codeCount[o.httpStatus] = (codeCount[o.httpStatus] || 0) + 1; });
  const chipList = [['all', '全部', 'var(--dim)', (DATA.orders || []).length]]
    .concat(Object.entries(codeCount).sort((a, b) => b[1] - a[1])
      .map(([c, n]) => [c, SHORT[c], COLOR[c], n]));
  const chips = `<div class="chips">${{chipList.map(([v, t, col, n]) => `
    <button class="chip-btn${{LOG_FILTER === v ? ' on' : ''}}" data-filter="${{v}}"
      type="button" aria-pressed="${{LOG_FILTER === v}}">
      ${{v === 'all' ? '' : `<span class="sw" style="background:${{col}}"></span>`}}
      ${{esc(t)}}<span class="n">${{n}}</span>
    </button>`).join('')}}</div>`;

  const log = slice.map(o => `
    <tr>
      <td class="mono" style="white-space:nowrap">${{o.datetime.replace(' ','<br>')}}
        <div style="color:var(--dim);font-size:10px;margin-top:3px">${{esc(o.store)}}</div></td>
      <td><span class="code mono" style="background:${{COLOR[o.httpStatus]}};color:#fff">${{SHORT[o.httpStatus]}}</span>
        <div class="reason" style="color:${{COLOR[o.httpStatus]}}">${{esc(o.codeTitle)}}</div>
        <div class="reason">${{esc(o.reason)}}</div></td>
      <td><details><summary>${{o.items.length}} 件商品（${{o.matchCoverage}} 可计量）▾</summary>
        ${{o.items.map(i => `<div class="item ${{i.matched?'':'miss'}}">${{i.qty}}× ${{esc(i.name)}}${{i.matched?` · ${{i.kcal}} kcal`:''}}</div>`).join('')}}
      </details></td>
      <td class="mono" style="text-align:right;white-space:nowrap">${{o.kcal ?? '—'}}
        <div style="color:var(--dim);font-size:10px">${{o.sodium!=null?o.sodium+' mg':''}}</div></td>
    </tr>`).join('');

  // 分页器：首/末 + 当前页邻域，页码用省略号收敛
  const pgBtn = (label, target, opt = {{}}) => {{
    const dis = opt.disabled ? 'disabled' : '';
    const on = opt.on ? ' class="pg-btn on"' : ' class="pg-btn"';
    return `<button${{on}} data-page="${{target}}" ${{dis}} type="button"
      ${{opt.label ? `aria-label="${{opt.label}}"` : ''}}>${{label}}</button>`;
  }};
  const nums = [];
  const push = n => nums.push(pgBtn(String(n), n, {{ on: n === page }}));
  if (pages <= 7) {{
    for (let i = 1; i <= pages; i++) push(i);
  }} else {{
    push(1);
    if (page > 3) nums.push('<span class="pg-gap">…</span>');
    for (let i = Math.max(2, page - 1); i <= Math.min(pages - 1, page + 1); i++) push(i);
    if (page < pages - 2) nums.push('<span class="pg-gap">…</span>');
    push(pages);
  }}
  const pager = `
    <div class="pager">
      <span class="pager-info">第 ${{(page - 1) * PER_PAGE + 1}}–${{Math.min(page * PER_PAGE, filtered.length)}} 条，
        共 ${{filtered.length}} 单${{pages > 1 ? ` · ${{pages}} 页` : ''}}</span>
      ${{pgBtn('‹', page - 1, {{ disabled: page === 1, label: '上一页' }})}}
      ${{nums.join('')}}
      ${{pgBtn('›', page + 1, {{ disabled: page === pages, label: '下一页' }})}}
    </div>`;

  const zone = on1024 ? `
    <div style="text-align:center;padding:20px">
      <div class="stat mono" style="font-size:42px;color:var(--yellow)">${{s.flowUnit}}</div>
      <div class="stat-note" style="margin-top:9px">
        按 1 kcal = 1 Byte、1024 进制换算，你的身体服务本期共传输 ${{(s.totalKcal||0).toLocaleString()}} kcal。<br>
        没有丢包，全是 TCP（贪吃 Protocol）。
      </div>
    </div>`
    : `<div class="locked">🔒 1024 限定区将于 10 月 20 日解锁 —— 届时摄入总量将换算为流量单位（1 kcal = 1 Byte）</div>`;

  document.getElementById('app').innerHTML =
    topbar(on1024 ? ' on' : '', on1024 ? '1024 模式：已激活' : '1024 模式：10/20–10/26 自动激活') +
    `<div class="grid4">${{hero}}</div>
    <div class="grid">${{second}}</div>
    <div class="grid4" style="margin-bottom:10px">
      <div class="panel">
        <div class="panel-h"><span class="dot" style="background:var(--yellow)"></span><h3>监控告警</h3></div>
        ${{(s.alerts||[]).map(a => `<div class="alert">${{esc(a)}}</div>`).join('') || '<div class="stat-note">无告警</div>'}}
        <div class="panel-h" style="margin-top:13px">
          <span class="dot" style="background:var(--orange)"></span><h3>错误预算消耗</h3></div>
        <div style="display:flex;align-items:baseline;gap:7px;margin-bottom:7px">
          <span class="mono" style="font-size:22px;font-weight:700;color:var(--orange)">${{s.errorBudgetUsed}}</span>
          <span class="stat-note" style="margin:0">次 4xx/5xx · 共 ${{s.totalOrders}} 单</span>
        </div>
        <div class="bar" style="height:6px"><div style="width:${{s.totalOrders ? Math.round(s.errorBudgetUsed/s.totalOrders*100) : 0}}%;background:var(--orange)"></div></div>
        <div class="stat-note" style="margin-top:7px">
          206 残缺响应属信息类，不计入错误预算
        </div>
        <div class="panel-h" style="margin-top:14px">
          <span class="dot" style="background:var(--cyan)"></span><h3>SLA 分级</h3></div>
        <div class="sla">
          ${{[
            {{min: 99, label: '金牌 SLA', c: 'var(--green)'}},
            {{min: 95, label: '银牌', c: 'var(--cyan)'}},
            {{min: 90, label: '铜牌', c: 'var(--yellow)'}},
            {{min: 0, label: 'Best Effort', c: 'var(--dim)'}},
          ].map(x => {{
            const on = m.uptime >= x.min;
            return `<div class="sla-row">
              <span class="sla-dot" style="background:${{on ? x.c : 'var(--panel2)'}}"></span>
              <span class="sla-lb" style="color:${{on ? 'var(--text)' : 'var(--dim)'}}">${{x.label}}</span>
              <span class="sla-v">≥${{x.min}}%</span>
              <span class="sla-s" style="color:${{on ? x.c : 'var(--dim)'}}">${{on ? '达标' : '未达标'}}</span>
            </div>`;
          }}).join('')}}
        </div>
        <div class="stat-note" style="margin-top:8px">
          当前 Uptime ${{m.uptime}}% · 依据本维度口径判定
        </div>
      </div>
      <div class="panel">
        <div class="panel-h"><span class="dot" style="background:var(--red)"></span><h3>营养账本缺口</h3></div>
        <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:9px">
          <span class="mono" style="font-size:20px;font-weight:700;color:${{cov>=60?'var(--green)':(cov>=40?'var(--yellow)':'var(--red)')}}">${{cov}}<small style="font-size:11px;color:var(--muted)">% 可计量</small></span>
          <span class="stat-note" style="margin:0">副指标 · 不计入错误预算</span>
        </div>
        ${{gapList || '<div class="stat-note">全部商品均可计量</div>'}}
        <div class="stat-note" style="margin-top:9px">官方营养账本仅收录 160 项标准单品所致</div>
      </div>
    </div>
    <div class="panel" id="logPanel" style="margin-bottom:10px">
      <div class="panel-h row" style="margin-bottom:11px">
        <div><span class="dot" style="background:var(--purple)"></span>
          <h3>请求日志 · 每单一次响应</h3></div>
        ${{chips}}
      </div>
      <table>
        <thead><tr>
          <th style="width:132px">时间 / 门店</th><th style="width:216px">状态码 / 诊断</th>
          <th>响应体（商品明细）</th><th style="width:78px;text-align:right">热量 / 钠</th>
        </tr></thead>
        <tbody>${{log}}</tbody>
      </table>
      ${{filtered.length ? pager : '<div class="stat-note" style="padding-top:12px;text-align:center">该筛选下暂无订单</div>'}}
    </div>
    <div class="panel">
      <div class="panel-h"><span class="dot" style="background:var(--yellow)"></span><h3>1024 程序员节限定区</h3></div>
      ${{zone}}
    </div>
    <footer>
      语义唯一视角：你是主体，你的身体是服务端 —— 全部状态码只描述你的身体对这次摄入的响应<br>
      麦门监控台 · 基于麦当劳中国官方 MCP 构建 · 独立开发，非官方产品 · 输出仅供参考，不构成营养或医疗建议
    </footer>`;
}}

if (s.collectionStatus === '404') {{
  render404();
}} else {{
  // 三类交互状态彼此独立：统计维度 / 日志筛选 / 日志页码
  // 维度支持 URL 深链（#week / #day），便于按视图分享与回访
  const HASH_DIM = (location.hash || '').replace('#', '');
  let CURRENT = HASH_DIM === 'week' ? 'week' : 'day';
  let LOG_FILTER = 'all';
  let LOG_PAGE = 1;

  function draw() {{ render(CURRENT, LOG_FILTER, LOG_PAGE); }}

  document.addEventListener('click', e => {{
    // 统计维度
    const dimBtn = e.target.closest('[data-dim]');
    if (dimBtn) {{
      const d = dimBtn.getAttribute('data-dim');
      if (d !== CURRENT) {{ CURRENT = d; history.replaceState(null, '', '#' + d); draw(); }}
      dimBtn.focus();
      return;
    }}
    // 日志筛选
    const fBtn = e.target.closest('[data-filter]');
    if (fBtn) {{
      const f = fBtn.getAttribute('data-filter');
      if (f !== LOG_FILTER) {{ LOG_FILTER = f; LOG_PAGE = 1; draw(); }}
      fBtn.focus();
      return;
    }}
    // 日志翻页
    const pBtn = e.target.closest('[data-page]');
    if (pBtn && !pBtn.disabled) {{
      LOG_PAGE = parseInt(pBtn.getAttribute('data-page'), 10) || 1;
      draw();
      const cur = document.querySelector('.pg-btn.on');
      if (cur) cur.focus();
    }}
  }});

  // 键盘左右键翻页（焦点在日志面板内时）
  document.addEventListener('keydown', e => {{
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    const logPanel = e.target.closest?.('#logPanel');
    if (!logPanel) return;
    e.preventDefault();
    const total = Object.keys(codeCountGlobal()).length;
    if (total <= 1) return;
    LOG_PAGE = Math.min(total, Math.max(1,
      LOG_PAGE + (e.key === 'ArrowRight' ? 1 : -1)));
    draw();
    document.querySelector('.pg-btn.on')?.focus();
  }});

  function codeCountGlobal() {{
    const list = LOG_FILTER === 'all'
      ? (DATA.orders || [])
      : (DATA.orders || []).filter(o => o.httpStatus === LOG_FILTER);
    return {{ n: Math.max(1, Math.ceil(list.length / 5)) }};
  }}

  draw();
}}
</script>
</body>
</html>
"""


def main():
    base = Path(__file__).resolve().parent.parent
    data = json.loads((base / "data" / "classified.json").read_text(encoding="utf-8"))
    force = "--1024" in sys.argv
    logo_b64 = base64.b64encode((base / "docs" / "logo.png").read_bytes()).decode()

    # 只注入面板需要的字段，避免把完整语义字典（含 evidence 文案）塞进前端
    codes_view = {k: {"color": v["color"], "short": v["short"], "title": v["title"]}
                  for k, v in CODE_META.items()}

    # TEMPLATE 里的 {{ }} 是为 Python .format() 转义准备的，但本脚本用 .replace()
    # 做占位符注入，因此必须先还原成单层花括号，否则前端 JS 语法错误、页面空白。
    # 顺序很关键：先还原模板 → 再注入 JSON。
    # 若顺序颠倒，注入的 JSON 中嵌套对象天然的 }} 会被误还原，导致数据损坏。
    tpl = re.sub(r"\{\{|\}\}", lambda m: m.group(0)[0], TEMPLATE)

    html = (tpl
            .replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__CODES__", json.dumps(codes_view, ensure_ascii=False))
            .replace("__KCAL_OK__", str(KCAL_OK))
            .replace("__KCAL_OVERLOAD__", str(KCAL_OVERLOAD))
            .replace("__FORCE_1024__", "true" if force else "false")
            .replace("__LOGO_B64__", logo_b64))

    out = base / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"✓ 已生成 {out}（{len(html)//1024} KB）浏览器直接打开即可")


if __name__ == "__main__":
    main()