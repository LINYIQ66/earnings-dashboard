#!/usr/bin/env python3
"""
美股财报数据管理器
- 自动抓取财报数据（过去30天 + 未来10天）
- 保存原始数据为 JSON（按日期归档）
- 超过30天的数据自动归档到 archive/
- 支持搜索历史数据（按代码、日期、惊喜幅度）
- 生成 HTML 报告
"""

import datetime as dt
import json
import math
import os
import shutil
import sys
from pathlib import Path

import yfinance as yf

# ── 目录配置 ──
BASE_DIR = Path.home() / "earnings-data"
REPORTS_DIR = BASE_DIR / "reports"
ARCHIVE_DIR = BASE_DIR / "archive"
DB_DIR = BASE_DIR / "db"

for d in [REPORTS_DIR, ARCHIVE_DIR, DB_DIR]:
    d.mkdir(parents=True, exist_ok=True)

TOP_US_STOCKS = [
    "NVDA","MSFT","AAPL","AMZN","GOOGL","META","AVGO","TSLA","BRK-B",
    "LLY","JPM","V","UNH","XOM","MA","COST","WMT","NFLX","PG","JNJ",
    "HD","ABBV","BAC","KO","PM","ORCL","CVX","CRM","MRK","AMD","CSCO",
    "PEP","IBM","MCD","GE","TMO","ABT","LIN","WFC","DIS","INTU","QCOM",
    "AXP","VZ","AMGN","TXN","NOW","ISRG","CAT","NFLX","PLTR","ARM",
    "SMCI","MU","DELL","SNOW","CRWD","ZS","PANW","SHOP",
]


def safe_float(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def get_company_name(ticker):
    try:
        return yf.Ticker(ticker).info.get("shortName", ticker)
    except Exception:
        return ticker


def fetch_earnings(tickers, past_days=30, future_days=10):
    today = dt.date.today()
    past_start = today - dt.timedelta(days=past_days)
    future_end = today + dt.timedelta(days=future_days)
    results = []
    name_cache = {}

    for i, ticker in enumerate(tickers):
        sys.stdout.write(f"\r  查询 {ticker} ({i+1}/{len(tickers)})...")
        sys.stdout.flush()
        try:
            ed = yf.Ticker(ticker).get_earnings_dates(limit=20)
            if ed is None or ed.empty:
                continue
            for idx, row in ed.iterrows():
                try:
                    rd = idx.date() if hasattr(idx, "date") else dt.datetime.fromisoformat(str(idx)).date()
                except Exception:
                    continue
                if not (past_start <= rd <= future_end):
                    continue
                actual = safe_float(row.get("Reported EPS"))
                expected = safe_float(row.get("EPS Estimate"))
                surprise = None
                if actual is not None and expected is not None and expected != 0:
                    surprise = round((actual - expected) / abs(expected) * 100, 2)
                status = "reported" if rd <= today else "upcoming"
                if status == "upcoming" and actual is not None:
                    status = "reported"
                if status == "reported" and actual is None:
                    status = "upcoming"
                if ticker not in name_cache:
                    name_cache[ticker] = get_company_name(ticker)
                results.append({
                    "ticker": ticker,
                    "name": name_cache[ticker],
                    "report_date": rd.isoformat(),
                    "eps_actual": actual,
                    "eps_expected": expected,
                    "surprise_pct": surprise,
                    "status": status,
                    "fetched_at": dt.datetime.now().isoformat(),
                })
        except Exception:
            pass
    print()
    return results


def save_raw_data(results):
    """保存今日原始数据到 JSON"""
    today = dt.date.today().isoformat()
    filepath = DB_DIR / f"earnings_{today}.json"
    # 合并已有数据（去重）
    existing = []
    if filepath.exists():
        with open(filepath, "r") as f:
            existing = json.load(f)
    seen = {(r["ticker"], r["report_date"]) for r in existing}
    new = [r for r in results if (r["ticker"], r["report_date"]) not in seen]
    combined = existing + new
    with open(filepath, "w") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    print(f"💾 保存原始数据: {filepath} ({len(new)} 新增, {len(combined)} 总计)")
    return combined


def archive_old_data():
    """将超过30天的数据文件移到 archive/"""
    cutoff = dt.date.today() - dt.timedelta(days=30)
    archived = 0
    for fp in sorted(DB_DIR.glob("earnings_*.json")):
        try:
            date_str = fp.stem.replace("earnings_", "")
            file_date = dt.date.fromisoformat(date_str)
            if file_date < cutoff:
                dest = ARCHIVE_DIR / fp.name
                shutil.move(str(fp), str(dest))
                archived += 1
                print(f"📦 归档: {fp.name} → archive/")
        except (ValueError, OSError):
            pass
    if archived == 0:
        print("📦 无需要归档的旧数据")
    else:
        print(f"📦 共归档 {archived} 个文件")
    return archived


def load_all_data():
    """加载所有数据（当前 + 归档）"""
    all_data = []
    for d in [DB_DIR, ARCHIVE_DIR]:
        for fp in sorted(d.glob("earnings_*.json")):
            try:
                with open(fp, "r") as f:
                    all_data.extend(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
    return all_data


def search_data(query):
    """搜索历史数据
    query 支持:
      - 股票代码: "NVDA", "AAPL"
      - 日期范围: "2026-05" (整月), "2026-05-01~2026-05-15"
      - 惊喜幅度: ">10" (超预期10%+), "<-5" (低于预期5%+)
      - 组合: "NVDA >5"
    """
    all_data = load_all_data()
    results = []

    # 解析查询条件
    ticker_filter = None
    date_filter = None
    surprise_filter = None
    surprise_op = None

    parts = query.strip().split()
    for part in parts:
        if part.startswith(">") or part.startswith("<"):
            try:
                surprise_op = part[0]
                surprise_filter = float(part[1:])
            except ValueError:
                pass
        elif "~" in part:
            date_filter = part  # range
        elif len(part) == 10 and part[4] == "-" and part[7] == "-":
            date_filter = part  # single date
        elif len(part) == 7 and part[4] == "-":
            date_filter = part  # month
        elif part.isalpha() and len(part) <= 6:
            ticker_filter = part.upper()

    for r in all_data:
        # Ticker filter
        if ticker_filter and ticker_filter not in r["ticker"].upper():
            continue
        # Date filter
        if date_filter:
            rd = r["report_date"]
            if "~" in date_filter:
                start, end = date_filter.split("~")
                if not (start <= rd <= end):
                    continue
            elif len(date_filter) == 7:  # month
                if not rd.startswith(date_filter):
                    continue
            else:
                if rd != date_filter:
                    continue
        # Surprise filter
        if surprise_filter is not None and surprise_op:
            s = r.get("surprise_pct")
            if s is None:
                continue
            if surprise_op == ">" and s <= surprise_filter:
                continue
            if surprise_op == "<" and s >= surprise_filter:
                continue
        results.append(r)

    # Sort by date desc, then surprise desc
    results.sort(key=lambda x: (x["report_date"], x.get("surprise_pct") or 0), reverse=True)
    return results


def print_search_results(results, query):
    """打印搜索结果"""
    if not results:
        print(f"🔍 搜索 '{query}' — 无结果")
        return

    print(f"\n🔍 搜索 '{query}' — 找到 {len(results)} 条记录\n")
    print(f"{'代码':<7} {'公司':<20} {'日期':<12} {'实际EPS':>10} {'预期EPS':>10} {'惊喜':>10} {'状态':<8}")
    print("-" * 80)
    for r in results:
        act = f"${r['eps_actual']:.2f}" if r["eps_actual"] is not None else "—"
        exp = f"${r['eps_expected']:.2f}" if r["eps_expected"] is not None else "—"
        sur = f"{r['surprise_pct']:+.1f}%" if r["surprise_pct"] is not None else "—"
        sur_color = ""
        if r["surprise_pct"] is not None:
            sur_color = "🟢" if r["surprise_pct"] > 0 else "🔴" if r["surprise_pct"] < 0 else "⚪"
        print(f"{r['ticker']:<7} {r['name'][:18]:<20} {r['report_date']:<12} {act:>10} {exp:>10} {sur_color}{sur:>9} {r['status']:<8}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="美股财报数据管理器")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("fetch", help="抓取最新财报数据")
    sub.add_parser("archive", help="归档超过30天的数据")
    sub.add_parser("stats", help="显示数据统计")

    sp_search = sub.add_parser("search", help="搜索历史数据")
    sp_search.add_argument("query", help="搜索条件（代码/日期/惊喜幅度）")

    args = parser.parse_args()

    if args.cmd == "fetch" or args.cmd is None:
        print("📊 抓取美股财报数据（过去30天 + 未来10天）...")
        results = fetch_earnings(TOP_US_STOCKS)
        save_raw_data(results)
        archive_old_data()
        reported = [r for r in results if r["status"] == "reported"]
        upcoming = [r for r in results if r["status"] == "upcoming"]
        beats = [r for r in reported if r.get("surprise_pct") and r["surprise_pct"] > 0]
        misses = [r for r in reported if r.get("surprise_pct") and r["surprise_pct"] < 0]
        print(f"\n✅ 已发布: {len(reported)} | 超预期: {len(beats)} | 低于预期: {len(misses)} | 待发布: {len(upcoming)}")

    elif args.cmd == "archive":
        archive_old_data()

    elif args.cmd == "search":
        results = search_data(args.query)
        print_search_results(results, args.query)

    elif args.cmd == "stats":
        all_data = load_all_data()
        db_files = list(DB_DIR.glob("earnings_*.json"))
        arc_files = list(ARCHIVE_DIR.glob("earnings_*.json"))
        print(f"\n📊 数据统计")
        print(f"  当前数据文件: {len(db_files)}")
        print(f"  归档数据文件: {len(arc_files)}")
        print(f"  总记录数: {len(all_data)}")
        tickers = set(r["ticker"] for r in all_data)
        dates = sorted(set(r["report_date"] for r in all_data))
        print(f"  覆盖股票: {len(tickers)} 只")
        if dates:
            print(f"  日期范围: {dates[0]} ~ {dates[-1]}")


if __name__ == "__main__":
    main()
