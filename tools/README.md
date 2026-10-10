# tools · 开发者辅助脚本

这些脚本**不是项目运行的一部分**，主程序（`scripts/`）仍然是纯标准库零依赖。

| 脚本 | 用途 | 依赖 |
|---|---|---|
| `shot.js` | 截取 dashboard 面板图片（用于 README 配图） | Node + `playwright-core` |
| `shot2.js` | 同上，支持按维度（`day` / `week`）切换后截图 | 同上 |

之所以放在 `tools/`：它们只为维护文档配图服务，不参与分类与渲染主流程，
因此不放在 `scripts/` 混淆「零依赖」的定位。

```bash
npm install playwright-core   # 装在 ~/.workbuddy/binaries/node/workspace
node tools/shot2.js "file://$PWD/dashboard.html" docs/screenshot-normal.png day
```

> 注意：Chrome CLI 的 `--screenshot` 在 `--virtual-time-budget` 下截不到 JS 渲染结果，
> 必须用 playwright 的 `waitForFunction` 等 `app.innerHTML` 渲染完成再截图。
