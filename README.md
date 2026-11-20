# NBA 2026-27 排名预测积分榜

张颖 vs 陈锵 对 NBA 2026-27 赛季东西部 30 队排名的预测对照看板：实时更新、自动算分、附带油画战况横幅、赛季日走势与偏离归因。

## 在线访问

GitHub Pages：https://a13923917757-cell.github.io/nba-2026-27-prediction-board/

## 功能

- **顶部战况横幅**：自动显示当前领先方（张颖 → “张颖 KO 陈锵”；陈锵 → “陈锵 小胜 张颖”），插画同步切换为对应油画版本
- **赛季日走势**：页面底部折线图，逐日展示两人累计失分的变化
- **总分对比**：每队预测名次与实际名次的绝对差即失分，差 1 名扣 1 分，累计失分越低越好
- **逐队对照**：东西部切换，显示实际种子排名、两人预测名次与失分
- **最大失分**：双方单队失分 Top 6 条形图
- **偏离归因**：8 支关键球队为什么超出/低于预测（伤病、重建红利、换核心、卫冕后遗症等）
- **最近比赛日比分条**

## 数据与更新（三层兜底）

1. **实时**：页面直接请求 ESPN 接口（`cdn.espn.com/core/nba/standings`），每 5 分钟刷新一次
2. **同源快照**：`scripts/update_data.py` 抓取排名写入同源 `data.json`（服务器端无跨域问题，可挂到 GitHub Action 或任意定时任务）
3. **内置快照**：接口与 data.json 都不可用时，使用页面内置的 2026-11-20 数据

排名口径为官方种子排名（同战绩按交锋/分区细则决胜），数据源为 ESPN。

## 新增：赛季日走势折线图

页面底部有「赛季日走势」折线图：从 2026-10-20 常规赛首日到最近一个比赛日，每天比赛打完后的累计失分变化。

- 数据由 `scripts/build_history.py` 生成：逐日抓 ESPN 当日比分（只取常规赛 `season.type=2`），累加每队战绩后按「胜率 → 胜场 → 官方种子序」排出分区名次，再与两人固定预测相减累加。
- 生成结果写入 `history.json`，页面启动时读取并绘制 SVG 折线。
- 最后一天的计算结果与官方榜单一致（张颖 54 分 / 陈锵 68 分），可作对照校验。
- 赛季有新比赛日后，重新执行 `python3 scripts/build_history.py` 即可刷新走势。

## 文件结构

```
index.html                  单文件网站（含全部样式与逻辑）
assets/ko-zy-win.jpg        张颖领先版油画横幅
assets/ko-cq-win.jpg        陈锵领先版油画横幅
data.json                   Action 每小时生成的排名快照
scripts/update_data.py      抓取并生成 data.json
scripts/build_history.py    逐日重建战绩，生成 history.json
history.json                每日累计失分走势
.github/workflows/update-data.yml  每小时自动更新工作流
```

## 部署

纯静态站点，把仓库内容托管到任意静态服务即可（GitHub Pages / Vercel / Netlify / Nginx），无需构建与环境变量。

本地预览（必须走 http，否则跨域请求会被拦截）：

```bash
python3 -m http.server 8000
# 打开 http://localhost:8000
```

手动更新一次数据：

```bash
python3 scripts/update_data.py
```

## 每日自动更新

`scripts/daily_update.sh` 一条命令完成全流程：抓最新排名 → 重建逐日走势 → 提交并推送到本仓库。

```bash
bash scripts/daily_update.sh
```

当前已在云端挂了每天 17:20（北京时间）的定时任务执行该脚本，脚本把 `data.json`、`history.json`、`index.html`、`assets` 同步到本地克隆（默认 `~/nba-repo`）后推送，GitHub Pages 随之更新。GitHub 写权限凭据存放在 `~/.config/nba_gh_token`（不在仓库内）。

## 备注

- 横幅插画有两套（张颖 KO 版 / 陈锵小胜版），按当前战况自动切换。
- 走势图是「按每日战绩推算」，同战绩按官方种子序，个别比赛日缺失时曲线会跳过该日。
- 赛季初各队仅 15 场左右，名次波动大，结论仅供参考。
