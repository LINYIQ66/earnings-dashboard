#!/usr/bin/env python3
"""
☕ KOPI 美股财报日报 — 核心数据引擎
功能: 抓取财报 + 股价/市值/行业 + 生成 data.json + HTML 仪表盘
用于 cron job 或手动运行
"""
import datetime as dt
import json
import math
import sys
import time
from pathlib import Path

import yfinance as yf

# ── 路径配置 ──
BASE_DIR = Path.home() / "earnings-data"
DB_DIR = BASE_DIR / "db"
REPORTS_DIR = BASE_DIR / "reports"
ARCHIVE_DIR = BASE_DIR / "archive"
CACHE_FILE = BASE_DIR / "company_cache.json"

for d in [DB_DIR, REPORTS_DIR, ARCHIVE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── 美股大盘 + 热门股 ──
TOP_US_STOCKS = [
    # 科技七巨头
    "NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META", "AVGO", "TSLA",
    # 金融
    "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP",
    # 医疗
    "UNH", "JNJ", "ABBV", "LLY", "MRK", "TMO", "ABT", "ISRG",
    # 消费
    "COST", "WMT", "PG", "KO", "PEP", "MCD", "HD", "DIS", "NFLX",
    # 能源/工业
    "XOM", "CVX", "GE", "CAT", "LIN",
    # 科技/半导体
    "ORCL", "CRM", "AMD", "CSCO", "IBM", "QCOM", "TXN", "NOW", "INTU",
    "MU", "SMCI", "DELL", "SNOW", "CRWD", "ZS", "PANW", "SHOP",
    # 通信
    "VZ", "T", "TMUS",
    # 其他蓝筹
    "BRK-B", "PM", "ARM", "PLTR",
]

# ── 行业映射 ──
SECTOR_MAP = {
    "NVDA": "半导体", "AMD": "半导体", "AVGO": "半导体", "QCOM": "半导体",
    "TXN": "半导体", "MU": "半导体", "ARM": "半导体", "SMCI": "半导体",
    "MSFT": "软件/云", "ORCL": "软件/云", "CRM": "软件/云", "NOW": "软件/云",
    "SNOW": "软件/云", "CRWD": "网络安全", "ZS": "网络安全", "PANW": "网络安全",
    "AAPL": "消费电子", "DELL": "消费电子",
    "AMZN": "电商/云", "SHOP": "电商/云",
    "GOOGL": "互联网", "META": "互联网", "NFLX": "互联网", "PLTR": "互联网",
    "TSLA": "汽车/能源",
    "JPM": "银行", "BAC": "银行", "WFC": "银行", "GS": "银行", "MS": "银行",
    "V": "支付", "MA": "支付", "AXP": "支付",
    "UNH": "医疗保险", "JNJ": "制药", "ABBV": "制药", "LLY": "制药",
    "MRK": "制药", "TMO": "医疗设备", "ABT": "医疗设备", "ISRG": "医疗设备",
    "COST": "零售", "WMT": "零售", "HD": "零售",
    "PG": "消费品", "KO": "消费品", "PEP": "消费品", "PM": "消费品",
    "MCD": "餐饮",
    "DIS": "娱乐/媒体",
    "XOM": "能源", "CVX": "能源",
    "GE": "工业", "CAT": "工业", "LIN": "化工",
    "CSCO": "网络设备", "IBM": "IT服务", "INTU": "金融科技",
    "VZ": "电信", "T": "电信", "TMUS": "电信",
    "BRK-B": "综合金融",
}


def safe_float(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def load_company_cache():
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_company_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def get_company_info(ticker, cache, fetch_detail=True):
    """获取公司信息（含缓存）"""
    if ticker in cache:
        return cache[ticker]

    info = {
        "name": ticker,
        "sector": SECTOR_MAP.get(ticker, "其他"),
        "market_cap": None,
        "price": None,
        "price_change_pct": None,
    }

    if not fetch_detail:
        cache[ticker] = info
        return info

    try:
        t = yf.Ticker(ticker)
        # 快速获取（批量属性）
        fast = t.fast_info if hasattr(t, "fast_info") else None
        if fast:
            info["price"] = safe_float(getattr(fast, "last_price", None))
            info["market_cap"] = safe_float(getattr(fast, "market_cap", None))

        # 获取名称和行业
        try:
            ti = t.info
            info["name"] = ti.get("shortName") or ti.get("longName") or ticker
            if not SECTOR_MAP.get(ticker):
                info["sector"] = ti.get("sector") or ti.get("industry") or "其他"
            if info["price"] is None:
                info["price"] = safe_float(ti.get("currentPrice") or ti.get("regularMarketPrice"))
            if info["market_cap"] is None:
                info["market_cap"] = safe_float(ti.get("marketCap"))
            # 当日涨跌
            info["price_change_pct"] = safe_float(
                ti.get("regularMarketChangePercent")
            )
        except Exception:
            pass

    except Exception:
        pass

    cache[ticker] = info
    return info


def fetch_earnings(tickers, past_days=30, future_days=10):
    """抓取财报数据 + 公司信息"""
    today = dt.date.today()
    past_start = today - dt.timedelta(days=past_days)
    future_end = today + dt.timedelta(days=future_days)

    cache = load_company_cache()
    results = []

    print(f"📊 抓取 {len(tickers)} 只股票财报数据...")
    print(f"   区间: {past_start} ~ {future_end}\n")

    for i, ticker in enumerate(tickers):
        pct = (i + 1) / len(tickers) * 100
        bar = "█" * int(pct / 4) + "░" * (25 - int(pct / 4))
        sys.stdout.write(f"\r  [{bar}] {ticker} ({i+1}/{len(tickers)})")
        sys.stdout.flush()

        try:
            ed = yf.Ticker(ticker).get_earnings_dates(limit=20)
            if ed is None or ed.empty:
                continue

            for idx, row in ed.iterrows():
                try:
                    rd = (
                        idx.date()
                        if hasattr(idx, "date")
                        else dt.datetime.fromisoformat(str(idx)).date()
                    )
                except Exception:
                    continue

                if not (past_start <= rd <= future_end):
                    continue

                actual = safe_float(row.get("Reported EPS"))
                expected = safe_float(row.get("EPS Estimate"))
                surprise = None
                if (
                    actual is not None
                    and expected is not None
                    and expected != 0
                ):
                    surprise = round((actual - expected) / abs(expected) * 100, 2)

                # 判断状态
                if actual is not None and rd <= today:
                    status = "reported"
                else:
                    status = "upcoming"

                # 获取公司信息（已发布的才详细抓取）
                fetch_detail = status == "reported"
                info = get_company_info(ticker, cache, fetch_detail=fetch_detail)

                results.append(
                    {
                        "ticker": ticker,
                        "name": info["name"],
                        "sector": info["sector"],
                        "report_date": rd.isoformat(),
                        "eps_actual": actual,
                        "eps_expected": expected,
                        "surprise_pct": surprise,
                        "status": status,
                        "market_cap": info["market_cap"],
                        "price": info["price"],
                        "price_change_pct": info["price_change_pct"],
                    }
                )
        except Exception as e:
            pass
        time.sleep(0.15)  # 限速

    save_company_cache(cache)
    print(f"\n✅ 抓取完成: {len(results)} 条记录")
    return results


def save_raw_data(results):
    """保存今日原始数据 + 合并历史"""
    today = dt.date.today().isoformat()
    filepath = DB_DIR / f"earnings_{today}.json"

    existing = []
    if filepath.exists():
        with open(filepath) as f:
            existing = json.load(f)

    seen = {(r["ticker"], r["report_date"]) for r in existing}
    new = [r for r in results if (r["ticker"], r["report_date"]) not in seen]
    combined = existing + new

    with open(filepath, "w") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"💾 保存: {filepath} ({len(new)} 新增, {len(combined)} 总计)")
    return combined


def archive_old_data():
    """归档超过30天的数据"""
    cutoff = dt.date.today() - dt.timedelta(days=30)
    count = 0
    for fp in sorted(DB_DIR.glob("earnings_*.json")):
        try:
            fd = dt.date.fromisoformat(fp.stem.replace("earnings_", ""))
            if fd < cutoff:
                import shutil

                shutil.move(str(fp), str(ARCHIVE_DIR / fp.name))
                count += 1
        except Exception:
            pass
    if count:
        print(f"📦 归档: {count} 个旧文件")


def load_all_data():
    """加载全部数据"""
    data = []
    for d in [DB_DIR, ARCHIVE_DIR]:
        for fp in sorted(d.glob("earnings_*.json")):
            try:
                with open(fp) as f:
                    data.extend(json.load(f))
            except Exception:
                pass
    return data


def generate_data_json(results):
    """生成前端用的 data.json"""
    all_data = load_all_data()
    today = dt.date.today()

    reported = [r for r in all_data if r["status"] == "reported"]
    upcoming = [r for r in all_data if r["status"] == "upcoming"]

    # 去重 + 排序
    seen = {}
    for r in reported:
        key = (r["ticker"], r["report_date"])
        if key not in seen:
            seen[key] = r
    reported_unique = sorted(
        seen.values(), key=lambda r: r.get("surprise_pct") or 0, reverse=True
    )

    upcoming_unique = sorted(
        upcoming, key=lambda r: r["report_date"]
    )

    beats = [r for r in reported_unique if r.get("surprise_pct") and r["surprise_pct"] > 0]
    misses = [r for r in reported_unique if r.get("surprise_pct") and r["surprise_pct"] < 0]
    flat = [r for r in reported_unique if r.get("surprise_pct") is not None and r["surprise_pct"] == 0]

    # 计算统计
    total = len(reported_unique)
    beat_rate = round(len(beats) / total * 100, 1) if total else 0
    miss_rate = round(len(misses) / total * 100, 1) if total else 0
    surprise_values = [r["surprise_pct"] for r in reported_unique if r.get("surprise_pct") is not None]
    avg_surprise = round(sum(surprise_values) / len(surprise_values), 2) if surprise_values else 0

    # 行业分析
    sector_stats = {}
    for r in reported_unique:
        sec = r.get("sector", "其他")
        if sec not in sector_stats:
            sector_stats[sec] = {"count": 0, "beats": 0, "misses": 0, "avg_surprise": 0, "surprises": []}
        sector_stats[sec]["count"] += 1
        if r.get("surprise_pct") and r["surprise_pct"] > 0:
            sector_stats[sec]["beats"] += 1
        elif r.get("surprise_pct") and r["surprise_pct"] < 0:
            sector_stats[sec]["misses"] += 1
        if r.get("surprise_pct") is not None:
            sector_stats[sec]["surprises"].append(r["surprise_pct"])

    for sec in sector_stats:
        surs = sector_stats[sec]["surprises"]
        sector_stats[sec]["avg_surprise"] = round(sum(surs) / len(surs), 2) if surs else 0
        del sector_stats[sec]["surprises"]

    # 按日期聚合（趋势图）
    date_trend = {}
    for r in reported_unique:
        d = r["report_date"]
        if d not in date_trend:
            date_trend[d] = {"date": d, "count": 0, "beats": 0, "misses": 0}
        date_trend[d]["count"] += 1
        if r.get("surprise_pct") and r["surprise_pct"] > 0:
            date_trend[d]["beats"] += 1
        elif r.get("surprise_pct") and r["surprise_pct"] < 0:
            date_trend[d]["misses"] += 1

    trend = sorted(date_trend.values(), key=lambda x: x["date"])

    # 市值排名（已发布）
    mkt_cap_ranking = sorted(
        [r for r in reported_unique if r.get("market_cap")],
        key=lambda r: r["market_cap"],
        reverse=True,
    )[:20]

    payload = {
        "meta": {
            "generated_at": dt.datetime.now().isoformat(),
            "report_date": today.isoformat(),
            "data_range": {
                "from": (today - dt.timedelta(days=30)).isoformat(),
                "to": (today + dt.timedelta(days=10)).isoformat(),
            },
        },
        "summary": {
            "total_reported": total,
            "total_upcoming": len(upcoming_unique),
            "beats": len(beats),
            "misses": len(misses),
            "flat": len(flat),
            "beat_rate": beat_rate,
            "miss_rate": miss_rate,
            "avg_surprise": avg_surprise,
        },
        "top_beats": beats[:20],
        "top_misses": misses[:20],
        "all_reported": reported_unique,
        "upcoming": upcoming_unique,
        "sectors": sector_stats,
        "trend": trend,
        "market_cap_ranking": mkt_cap_ranking,
        "watchlist": TOP_US_STOCKS,
    }

    data_json_path = REPORTS_DIR / "data.json"
    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"📊 生成 data.json: {data_json_path}")
    return payload


def generate_text_summary(data):
    """生成纯文本摘要（用于 cron 消息）"""
    s = data["summary"]
    top_beats = data["top_beats"][:5]
    top_misses = data["top_misses"][:5]
    upcoming = data["upcoming"][:10]

    summary = f"☕ 美股财报日报 {data['meta']['report_date']}\n"
    summary += f"已发布: {s['total_reported']} | 超预期: {s['beats']} | 低于预期: {s['misses']} | 待发布: {s['total_upcoming']}\n"
    summary += f"超预期率: {s['beat_rate']}% | 平均惊喜: {s['avg_surprise']:+.2f}%\n\n"

    if top_beats:
        summary += "🟢 最大超预期:\n"
        for r in top_beats:
            summary += f"  {r['ticker']:5s} {r['name'][:20]:20s} {r['surprise_pct']:+.1f}% (${r['eps_actual']:.2f}/${r['eps_expected']:.2f})\n"

    if top_misses:
        summary += "\n🔴 最大不及预期:\n"
        for r in top_misses:
            summary += f"  {r['ticker']:5s} {r['name'][:20]:20s} {r['surprise_pct']:+.1f}% (${r['eps_actual']:.2f}/${r['eps_expected']:.2f})\n"

    if upcoming:
        summary += f"\n📅 未来待发: {', '.join(r['ticker'] for r in upcoming[:8])}\n"

    summary += f"\n🌐 GitHub Pages: https://linyiq66.github.io/earnings-dashboard/\n"
    summary += f"📄 本地: {REPORTS_DIR / 'index.html'}\n"

    return summary


def main():
    today = dt.date.today()

    print("=" * 60)
    print(f"☕ KOPI 美股财报日报 · {today.isoformat()}")
    print("=" * 60)

    # Step 1: 抓取数据
    results = fetch_earnings(TOP_US_STOCKS)
    save_raw_data(results)
    archive_old_data()

    # Step 2: 生成 data.json
    data = generate_data_json(results)

    # Step 3: 生成 HTML 报告（如果 index.html 存在则跳过）
    html_path = REPORTS_DIR / "index.html"
    if not html_path.exists():
        print("⚠️  index.html 不存在，请先部署前端文件")
    else:
        print(f"📄 HTML 报告: {html_path}")

    # Step 4: 输出摘要
    print("\n" + "=" * 60)
    summary = generate_text_summary(data)
    print(summary)

    return summary


if __name__ == "__main__":
    print(main())
