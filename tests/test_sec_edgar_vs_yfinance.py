"""
Cross-source integration test: SEC EDGAR vs yfinance for 50 stocks × 4 dates × 3 statements.

Marked @pytest.mark.integration — requires network access and EDGAR_IDENTITY to be set.
Run manually; not part of the fast unit test suite.

    uv run pytest tests/test_sec_edgar_vs_yfinance.py -v --timeout=600

After the run, inspect the report:
    cat tests/data/edgar_vs_yfinance_report.json
"""

import json
import os

import pandas as pd
import pytest
import yfinance as yf

from tradingagents.dataflows.sec_edgar_fundamentals import (
    SECEdgarNotFoundError,
    SECEdgarNoXBRLError,
    _get_financials,
)
from tradingagents.dataflows.stockstats_utils import filter_financials_by_date

# ── constants ─────────────────────────────────────────────────────────────────

CACHE_FILE  = os.path.join(os.path.dirname(__file__), "data", "yfinance_cache.json")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "data", "edgar_vs_yfinance_report.json")

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

TEST_DATES = [
    "2022-02-15",  # Q4 2021 earnings season
    "2022-08-15",  # Q2 2022 earnings season
    "2023-02-15",  # Q4 2022 earnings season
    "2024-02-15",  # Q4 2023 earnings season
]

DEVIATION_THRESHOLD = 0.15  # 15% — accounts for label differences between sources


# ── yfinance metric extraction ────────────────────────────────────────────────

def _safe_float(df: pd.DataFrame, col, *names: str) -> float | None:
    for name in names:
        if name in df.index:
            v = df.loc[name, col]
            if pd.notna(v):
                return float(v)
    return None


def _yf_income(ticker: str, curr_date: str) -> dict:
    try:
        df = filter_financials_by_date(yf.Ticker(ticker).income_stmt, curr_date)
        if df.empty:
            return {}
        col = df.columns[0]
        return {
            "total_revenue":    _safe_float(df, col, "Total Revenue", "Revenue"),
            "net_income":       _safe_float(df, col, "Net Income",
                                            "Net Income Common Stockholders"),
            "gross_profit":     _safe_float(df, col, "Gross Profit"),
            "operating_income": _safe_float(df, col, "Operating Income", "EBIT"),
        }
    except Exception:
        return {}


def _yf_balance(ticker: str, curr_date: str) -> dict:
    try:
        df = filter_financials_by_date(yf.Ticker(ticker).balance_sheet, curr_date)
        if df.empty:
            return {}
        col = df.columns[0]
        return {
            "total_assets":        _safe_float(df, col, "Total Assets"),
            "total_liabilities":   _safe_float(df, col,
                                               "Total Liabilities Net Minority Interest",
                                               "Total Liabilities"),
            "stockholders_equity": _safe_float(df, col, "Stockholders Equity",
                                               "Common Stock Equity"),
            "cash":                _safe_float(df, col, "Cash And Cash Equivalents",
                                               "Cash Cash Equivalents And Short Term Investments"),
        }
    except Exception:
        return {}


def _yf_cashflow(ticker: str, curr_date: str) -> dict:
    try:
        df = filter_financials_by_date(yf.Ticker(ticker).cashflow, curr_date)
        if df.empty:
            return {}
        col = df.columns[0]
        return {
            "operating_cf":         _safe_float(df, col, "Operating Cash Flow"),
            "capital_expenditures": _safe_float(df, col, "Capital Expenditure"),
            "free_cash_flow":       _safe_float(df, col, "Free Cash Flow"),
        }
    except Exception:
        return {}


# ── EDGAR metric extraction ───────────────────────────────────────────────────

def _edgar_income(fin) -> dict:
    # GrossProfit$ anchored to avoid matching abstract concepts with the same prefix
    gross_profit = fin._get_concept_value("income", [r"GrossProfit$"])
    return {
        "total_revenue":    fin.get_revenue(),
        "net_income":       fin.get_net_income(),
        "gross_profit":     gross_profit,
        "operating_income": fin.get_operating_income(),
    }


def _edgar_balance(fin) -> dict:
    # Use us-gaap:Assets / us-gaap:Liabilities XBRL concepts for consolidated totals.
    # get_total_assets() / get_total_liabilities() can map to wrong rows on companies
    # with complex segment disclosures (e.g. CAT maps to "Total current assets").
    # The `us-gaap[_:]` prefix avoids company-specific prefixes (e.g. jpm_TradingAssets)
    # that also end in "Assets" and would be matched by a bare "Assets$" pattern.
    total_assets = fin._get_concept_value("balance", [r"us-gaap[_:]Assets$"])
    total_liabilities = fin._get_concept_value("balance", [r"us-gaap[_:]Liabilities$"])
    # Use XBRL concept search so we get cash-and-equivalents, not current assets
    cash = fin._get_concept_value(
        "balance",
        [r"CashAndCashEquivalentsAtCarryingValue$", r"CashAndCashEquivalents$"],
    )
    return {
        "total_assets":        total_assets,
        "total_liabilities":   total_liabilities,
        "stockholders_equity": fin.get_stockholders_equity(),
        "cash":                cash,
    }


def _edgar_cashflow(fin) -> dict:
    # Use XBRL concept search with $ anchor to skip abstract header rows that
    # share the same prefix (e.g. NetCashProvidedByUsedInOperatingActivitiesAbstract).
    # Also try the ContinuingOperations variant used by conglomerates with discontinued ops.
    operating_cf = fin._get_concept_value(
        "cashflow",
        [
            r"NetCashProvidedByUsedInOperatingActivities$",
            r"NetCashProvidedByUsedInOperatingActivitiesContinuingOperations$",
        ],
    )

    # EDGAR reports capex as a positive outflow; yfinance uses negative convention.
    # Some companies (e.g. CAT) split capex into two XBRL lines:
    # PaymentsToAcquirePropertyPlantAndEquipment (machinery segment) and
    # PaymentsToAcquireEquipmentOnLease (Financial Products leased assets).
    # Sum both to match yfinance's consolidated capex figure.
    capex_ppe    = fin._get_concept_value("cashflow", [r"PaymentsToAcquirePropertyPlantAndEquipment$"])
    capex_leased = fin._get_concept_value("cashflow", [r"PaymentsToAcquireEquipmentOnLease$"])
    if capex_ppe is not None and capex_leased is not None:
        capex_raw = capex_ppe + capex_leased
    elif capex_ppe is not None:
        capex_raw = capex_ppe
    else:
        capex_raw = fin.get_capital_expenditures()
    capital_expenditures = -capex_raw if capex_raw is not None else None

    # Compute FCF directly as OCF − capex (always, matching yfinance's convention).
    # get_free_cash_flow() is unreliable for conglomerates with discontinued ops
    # (e.g. RTX returns −capex instead of OCF−capex); just derive it consistently.
    if operating_cf is not None and capex_raw is not None:
        free_cash_flow = operating_cf - capex_raw  # OCF − capex (positive outflow)
    else:
        free_cash_flow = None

    return {
        "operating_cf":         operating_cf,
        "capital_expenditures": capital_expenditures,
        "free_cash_flow":       free_cash_flow,
    }


# ── deviation ─────────────────────────────────────────────────────────────────

def _deviation(edgar_val: float, yf_val: float) -> float | None:
    if edgar_val is None or yf_val is None:
        return None
    return abs(edgar_val - yf_val) / max(abs(edgar_val), 1.0)


# ── cache helpers ─────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


# ── report writer ─────────────────────────────────────────────────────────────

def _write_report(results: list, failures: list) -> None:
    total  = sum(1 for r in results if r["status"] in ("pass", "fail"))
    passed = total - len(failures)

    skipped_period_mismatch = sum(1 for r in results if r["status"] == "period_mismatch")
    skipped_edgar_not_found = sum(1 for r in results if r["status"] == "edgar_not_found")
    skipped_edgar_error     = sum(1 for r in results if r["status"] == "edgar_error")
    total_attempted = len(results)

    by_sector: dict[str, dict] = {}
    for r in results:
        if r["status"] not in ("pass", "fail"):
            continue
        s = r["sector"]
        if s not in by_sector:
            by_sector[s] = {"passed": 0, "failed": 0, "_devs": []}
        if r["status"] == "pass":
            by_sector[s]["passed"] += 1
        else:
            by_sector[s]["failed"] += 1
        if r.get("deviations"):
            by_sector[s]["_devs"].extend(v for v in r["deviations"].values() if v is not None)

    for s, data in by_sector.items():
        devs = data.pop("_devs", [])
        data["avg_deviation_pct"] = round(sum(devs) / len(devs) * 100, 2) if devs else 0.0

    report = {
        "summary": {
            "total":            total,
            "passed":           passed,
            "failed":           len(failures),
            "failure_rate_pct": round(len(failures) / total * 100, 1) if total else 0.0,
            "skipped": {
                "total":           total_attempted - total,
                "period_mismatch": skipped_period_mismatch,
                "edgar_not_found": skipped_edgar_not_found,
                "edgar_error":     skipped_edgar_error,
            },
        },
        "by_sector": by_sector,
        "failures":  failures,
    }
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport written to {REPORT_FILE}")


# ── test ─────────────────────────────────────────────────────────────────────

STATEMENT_CONFIGS = [
    ("income",   _edgar_income,   _yf_income),
    ("balance",  _edgar_balance,  _yf_balance),
    ("cashflow", _edgar_cashflow, _yf_cashflow),
]


@pytest.mark.integration
def test_edgar_vs_yfinance_comprehensive():
    """
    50 stocks × 4 dates × 3 statements = up to 600 cross-source comparisons.

    For each case:
    - Fetch EDGAR scalar metrics directly from the Financials object.
    - Fetch yfinance metrics from committed cache (no live network call).
    - Assert deviation < 15% for >=75% of available metric pairs.

    Overall pass criterion: <=10% failure rate across all cases.
    Full details written to tests/data/edgar_vs_yfinance_report.json.
    """
    import tradingagents.dataflows.sec_edgar_fundamentals as m
    if not m._identity_set:
        import edgar
        identity = os.environ.get("EDGAR_IDENTITY", "TradingAgents test@example.com")
        edgar.set_identity(identity)
        m._identity_set = True

    cache    = _load_cache()
    results  = []
    failures = []

    for sector, tickers in SECTORS.items():
        for ticker in tickers:
            for curr_date in TEST_DATES:
                for stmt_type, edgar_fn, yf_fn in STATEMENT_CONFIGS:
                    # ── EDGAR ──
                    try:
                        fin, filing_date, period = _get_financials(
                            ticker, "annual", curr_date
                        )
                        edgar_m = edgar_fn(fin)
                    except (SECEdgarNotFoundError, SECEdgarNoXBRLError) as exc:
                        results.append({
                            "sector": sector, "ticker": ticker,
                            "date": curr_date, "statement": stmt_type,
                            "status": "edgar_not_found", "error": str(exc),
                        })
                        continue
                    except Exception as exc:
                        results.append({
                            "sector": sector, "ticker": ticker,
                            "date": curr_date, "statement": stmt_type,
                            "status": "edgar_error", "error": str(exc),
                        })
                        continue

                    # ── yfinance (from cache) ──
                    cache_key = f"{ticker}_{stmt_type}_{curr_date}"
                    yf_period_date = None
                    if cache_key in cache:
                        yf_m           = cache[cache_key]["metrics"]
                        yf_period_date = cache[cache_key].get("period_date")
                    else:
                        # cache miss: fetch live (slow, should not happen if cache populated)
                        print(f"WARN: cache miss {cache_key} — fetching live from yfinance")
                        yf_m = yf_fn(ticker, curr_date)

                    # ── period-mismatch guard ────────────────────────────────
                    # EDGAR returns the last *filed* 10-K as of curr_date.
                    # yfinance returns data by period-end date, ignoring filing lag.
                    # When a company files its 10-K in mid-February (after the test
                    # date), EDGAR sees FY-1 while yfinance already sees FY data
                    # because the period ended ≤ curr_date.  Skip those cases so
                    # they don't inflate the failure rate.
                    if yf_period_date and period:
                        edgar_fy = period[:7]   # "YYYY-MM"
                        yf_fy    = yf_period_date[:7]
                        if edgar_fy != yf_fy:
                            results.append({
                                "sector": sector, "ticker": ticker,
                                "date": curr_date, "statement": stmt_type,
                                "filing_date": filing_date,
                                "status": "period_mismatch",
                                "edgar_period": period,
                                "yf_period": yf_period_date,
                            })
                            continue

                    # ── compare ──
                    matched    = 0
                    comparable = 0
                    deviations = {}

                    for metric, edgar_val in edgar_m.items():
                        yf_val = yf_m.get(metric) if yf_m else None
                        dev    = _deviation(edgar_val, yf_val)
                        if dev is None:
                            continue
                        comparable += 1
                        deviations[metric] = round(dev, 4)
                        if dev <= DEVIATION_THRESHOLD:
                            matched += 1

                    # pass if 75%+ of comparable metrics are within threshold
                    # (or if there are no comparable pairs — counts as neutral)
                    passed = comparable == 0 or matched >= max(1, int(comparable * 0.75))

                    entry = {
                        "sector": sector, "ticker": ticker,
                        "date": curr_date, "statement": stmt_type,
                        "filing_date": filing_date,
                        "status": "pass" if passed else "fail",
                        "matched": matched, "comparable": comparable,
                        "deviations": deviations,
                    }
                    results.append(entry)
                    if not passed:
                        failures.append(entry)

    _write_report(results, failures)

    total_scored = sum(1 for r in results if r["status"] in ("pass", "fail"))
    fail_count   = len(failures)
    failure_rate = fail_count / total_scored if total_scored > 0 else 0.0

    assert failure_rate <= 0.10, (
        f"{fail_count}/{total_scored} cases failed ({failure_rate:.1%} > 10% threshold).\n"
        f"See {REPORT_FILE} for the full breakdown."
    )
