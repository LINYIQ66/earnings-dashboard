# ☕ KOPI Earnings Dashboard 美股财报仪表盘

<p align="center">
  <img src="docs/screenshot.jpg" alt="KOPI Earnings Dashboard" width="600">
</p>

<p align="center">
  <b>AI-Powered US Stock Earnings Tracker · Real-Time · Interactive</b><br>
  <b>AI 驱动的美股财报追踪仪表盘 · 实时数据 · 交互式体验</b>
</p>

<p align="center">
  <a href="https://linyiq66.github.io/earnings-dashboard/"><img src="https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-2563eb?style=for-the-badge&logo=github" alt="Live Demo"></a>
  <a href="https://github.com/LINYIQ66/earnings-dashboard/actions"><img src="https://img.shields.io/badge/Auto%20Update-Daily-f59e0b?style=for-the-badge&logo=githubactions" alt="Auto Update"></a>
</p>

---

## ✨ Features · 功能

| 🇺🇸 English | 🇨🇳 中文 |
|------------|---------|
| **Real-time Earnings Data** — 60+ US stocks tracked daily via Yahoo Finance | **实时财报数据** — 追踪 60+ 只美股，通过 Yahoo Finance 每日更新 |
| **Interactive Dashboard** — Sort, search, and filter by ticker, sector, surprise % | **交互式仪表盘** — 按代码、行业、惊喜幅度排序/搜索/筛选 |
| **Trend Charts** — 30-day visual history of beats vs. misses | **趋势图表** — 30 天超预期 vs 低于预期可视化 |
| **Sector Analysis** — Industry-level breakdown of earnings performance | **行业分析** — 按行业细分的财报表现面板 |
| **Market Cap Ranking** — Real-time valuation & price data for reported companies | **市值排名** — 已发布公司的实时估值与股价 |
| **Upcoming Calendar** — 10-day lookahead for earnings releases | **待发布日历** — 未来 10 天财报发布时间线 |
| **Dark/Light Mode** — Toggle for day or night viewing | **深色/浅色模式** — 一键切换，护眼舒适 |
| **Daily Auto-Update** — GitHub Actions + local cron job keep data fresh | **每日自动更新** — GitHub Actions + 本地 cron 双重保障 |

## 📊 Data Coverage · 数据覆盖

**62 US Large-Cap Stocks** across 18 sectors:

科技七巨头 `NVDA` `MSFT` `AAPL` `AMZN` `GOOGL` `META` `AVGO` `TSLA` · 金融 `JPM` `BAC` `WFC` `GS` `MS` `V` `MA` `AXP` · 医疗 `UNH` `JNJ` `ABBV` `LLY` `MRK` `TMO` `ABT` `ISRG` · 消费 `COST` `WMT` `PG` `KO` `PEP` `MCD` `HD` `DIS` `NFLX` · 能源 `XOM` `CVX` · 工业 `GE` `CAT` `LIN` · 科技 `ORCL` `CRM` `AMD` `CSCO` `IBM` `QCOM` `TXN` `NOW` `INTU` `MU` `SMCI` `DELL` `SNOW` `CRWD` `ZS` `PANW` `SHOP` · 电信 `VZ` `T` `TMUS` · 其他 `BRK-B` `PM` `ARM` `PLTR`

## 🚀 Quick Start · 快速开始

### Prerequisites

```bash
pip install yfinance
```

### Run Locally

```bash
cd ~/earnings-data
python3 daily_update.py
```

This will:
1. Fetch earnings data for all 62 stocks (past 30 days + next 10 days)
2. Save raw data to `db/`
3. Generate `docs/data.json` for the dashboard
4. Print a text summary

### View Dashboard

Open `docs/index.html` in your browser, or visit the live demo.

## 🏗 Architecture · 架构

```
earnings-data/
├── daily_update.py          # Core engine: fetch + generate
├── earnings_manager.py      # CLI manager: search, stats, archive
├── docs/                    # Static site (GitHub Pages)
│   ├── index.html           # Interactive dashboard
│   ├── data.json            # Structured earnings data
│   └── screenshot.jpg       # Preview image
├── db/                      # Daily raw data (JSON, 30-day rolling)
├── archive/                 # Older archived data
└── .github/workflows/
    └── update.yml           # GitHub Actions daily auto-update
```

## ⚙️ Automation · 自动化

| Method | Schedule | Description |
|--------|----------|-------------|
| **GitHub Actions** | Weekdays UTC 10:00 | Fetches data, commits & pushes `data.json` |
| **KOPI Cron Job** | Daily 12:00 (UTC+8) | Runs locally, pushes to GitHub |

Both methods run `daily_update.py` → generate `data.json` → commit & push to `main` → GitHub Pages auto-deploys from `/docs`.

## 🎨 Design · 设计

- **Color Palette**: KOPI Coffee Theme — Deep Navy `#0f0f1a`, Blue `#2563eb`, Gold `#f59e0b`
- **Typography**: SF Pro / system font stack
- **Responsive**: Mobile-first, works on all screen sizes
- **Zero Dependencies**: Pure HTML/CSS/JS, no frameworks

## 📝 License

MIT — feel free to fork and customize.

---

<p align="center">
  <sub>☕ Powered by <a href="https://kopiaiagent.com">KOPI AI Agent</a> · Data from Yahoo Finance · Not financial advice</sub><br>
  <sub>⚠️ 数据仅供参考，不构成投资建议</sub>
</p>
