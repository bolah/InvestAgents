#!/usr/bin/env python3
"""
Pre-populate tests/data/yfinance_cache.json with yfinance scalar metrics.

Run once manually before executing the 50-stock comparison tests.
The resulting cache file is committed so CI never hits yfinance live.

Usage:
    uv run python tests/scripts/populate_yfinance_cache.py

The script is idempotent: it skips keys already present in the cache.
"""

import json
import os
import sys
import time

import pandas as pd
import yfinance as yf

# Allow importing from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from tradingagents.dataflows.stockstats_utils import filter_financials_by_date

CACHE_FILE = os.path.join(os.path.dirname(__file__), "../data/yfinance_cache.json")

SECTORS = {
    "Technology":             ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "Healthcare":             ["JNJ",  "UNH",  "LLY",  "PFE",  "ABBV"],
    "Financials":             ["JPM",  "BAC",  "WFC",  "GS",   "MS"],
    "Consumer_Discretionary": ["AMZN", "TSLA", "HD",   "MCD",  "NKE"],
    "Consumer_Staples":       ["PG",   "KO",   "PEP",  "WMT",  "COST"],
    "Energy":                 ["XOM",  "CVX",  "COP",  "SLB",  "EOG"],
    "Industrials":            ["CAT",  "HON",  "GE",   "UNP",  "RTX"],
    "Utilities":              ["NEE",  "DUK",  "SO",   "D",    "AEP"],
    "Materials":              ["LIN",  "APD",  "ECL",  "DD",   "NEM"],
    "Real_Estate":            ["AMT",  "PLD",  "CCI",  "EQIX", "SPG"],
}

ALL_TICKERS = [t for tickers in SECTORS.values() for t in tickers]
TEST_DATES  = ["2022-02-15", "2022-08-15", "2023-02-15", "2024-02-15"]


def _safe_float(df: pd.DataFrame, col, *row_names: str):
    for name in row_names:
        if name in df.index:
            v = df.loc[name, col]
            if pd.notna(v):
                return float(v)
    return None


def _income_metrics(ticker: str, curr_date: str) -> dict:
    try:
        df = filter_financials_by_date(yf.Ticker(ticker).income_stmt, curr_date)
        if df.empty:
            return {}
        col = df.columns[0]
        return {
            "total_revenue":    _safe_float(df, col, "Total Revenue", "Revenue"),
            "net_income":       _safe_float(df, col, "Net Income", "Net Income Common Stockholders"),
            "gross_profit":     _safe_float(df, col, "Gross Profit"),
            "operating_income": _safe_float(df, col, "Operating Income", "EBIT"),
        }
    except Exception as e:
        print(f"    [WARN] income {ticker} {curr_date}: {e}")
        return {}


def _balance_metrics(ticker: str, curr_date: str) -> dict:
    try:
        df = filter_financials_by_date(yf.Ticker(ticker).balance_sheet, curr_date)
        if df.empty:
            return {}
        col = df.columns[0]
        return {
            "total_assets":       _safe_float(df, col, "Total Assets"),
            "total_liabilities":  _safe_float(df, col,
                                              "Total Liabilities Net Minority Interest",
                                              "Total Liabilities"),
            "stockholders_equity": _safe_float(df, col, "Stockholders Equity",
                                               "Common Stock Equity"),
            "cash":               _safe_float(df, col, "Cash And Cash Equivalents",
                                              "Cash Cash Equivalents And Short Term Investments"),
        }
    except Exception as e:
        print(f"    [WARN] balance {ticker} {curr_date}: {e}")
        return {}


def _cashflow_metrics(ticker: str, curr_date: str) -> dict:
    try:
        df = filter_financials_by_date(yf.Ticker(ticker).cashflow, curr_date)
        if df.empty:
            return {}
        col = df.columns[0]
        return {
            "operating_cf":        _safe_float(df, col, "Operating Cash Flow"),
            "capital_expenditures": _safe_float(df, col, "Capital Expenditure"),
            "free_cash_flow":       _safe_float(df, col, "Free Cash Flow"),
        }
    except Exception as e:
        print(f"    [WARN] cashflow {ticker} {curr_date}: {e}")
        return {}


EXTRACTORS = {
    "income":   _income_metrics,
    "balance":  _balance_metrics,
    "cashflow": _cashflow_metrics,
}


def main():
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} existing cache entries.")

    total   = len(ALL_TICKERS) * len(TEST_DATES) * len(EXTRACTORS)
    done    = 0
    skipped = 0

    for ticker in ALL_TICKERS:
        print(f"\n{ticker}")
        for curr_date in TEST_DATES:
            for stmt_type, fn in EXTRACTORS.items():
                key = f"{ticker}_{stmt_type}_{curr_date}"
                if key in cache:
                    done += 1
                    skipped += 1
                    continue
                metrics = fn(ticker, curr_date)
                cache[key] = {"metrics": metrics}
                done += 1
                print(f"  [{done}/{total}] {key}: {[k for k, v in metrics.items() if v is not None]}")
                time.sleep(0.4)  # polite to yfinance rate limits

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

    print(f"\nDone. {len(cache)} entries in cache ({skipped} skipped/cached). → {CACHE_FILE}")


if __name__ == "__main__":
    main()
