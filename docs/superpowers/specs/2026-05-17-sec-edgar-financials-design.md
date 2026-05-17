# SEC EDGAR Financial Statements Integration — Design Spec

**Date:** 2026-05-17  
**Status:** Approved  
**Phase:** 8 — Replace yfinance with SEC EDGAR for financial statements

---

## Problem

yfinance uses web scraping for historical financial statements. It has documented gaps (missing fiscal periods), inconsistencies (misaligned column dates), and no reliability guarantees. SEC EDGAR provides the same data directly from the official XBRL filings that companies are legally required to file — complete, machine-readable, and stable.

---

## Goals

1. Replace `get_balance_sheet`, `get_cashflow`, and `get_income_statement` with SEC EDGAR-backed implementations.
2. Keep `get_fundamentals` (ticker.info market metrics: PE, market cap, EV) on yfinance — these have no XBRL equivalent.
3. Slot SEC EDGAR in as a new `"sec_edgar"` vendor in the existing routing layer with zero agent-level changes.
4. Prevent look-ahead bias using SEC filing date as the anchor (not fiscal period end date).
5. Add an optional cross-validation mode that compares EDGAR vs yfinance on key metrics.
6. Provide a comprehensive data quality test suite covering 50 stocks across sectors.

---

## Library Choice: `edgartools` (`edgar` package)

- **Free, no API key** — connects directly to `data.sec.gov`
- **Built-in rate limiting** — defaults to 8 req/s (respects SEC's 10 req/s cap)
- **`to_markdown()` output** — LLM-ready tables, perfect for downstream agents
- **Clean date filtering** — `Company(ticker).get_filings(form='10-K', date=('2000-01-01', curr_date))` returns only filings with `filing_date ≤ curr_date`
- **Actively maintained** — version 5.31.2 released May 15, 2026 (MIT license)

---

## Architecture

### Files Changed

| File | Change |
|---|---|
| `tradingagents/dataflows/sec_edgar_fundamentals.py` | **NEW** — edgartools-backed implementations |
| `tradingagents/dataflows/interface.py` | Add `"sec_edgar"` vendor entries for 3 statement functions |
| `tradingagents/default_config.py` | Change `fundamental_data` default from `"yfinance"` to `"sec_edgar"` |
| `tests/test_sec_edgar_fundamentals.py` | **NEW** — unit + integration + cross-validation tests |
| `tests/data/yfinance_cache.json` | **NEW** — cached yfinance responses for 50-stock comparison test |

No changes to agent files, graph wiring, `AgentState`, or CLI.

### Vendor Routing After Change

```
interface.py VENDOR_METHODS["fundamental_data"] category:

  get_balance_sheet:      sec_edgar (default)  →  alpha_vantage  →  yfinance
  get_cashflow:           sec_edgar (default)  →  alpha_vantage  →  yfinance
  get_income_statement:   sec_edgar (default)  →  alpha_vantage  →  yfinance
  get_fundamentals:       alpha_vantage (default) → yfinance   [UNCHANGED]
```

---

## `sec_edgar_fundamentals.py` Design

### Identity

SEC requires a `User-Agent` header. `edgar.set_identity()` must be called before any request. Read from `EDGAR_IDENTITY` env var (e.g. `"TradingAgents user@example.com"`). Raise `EnvironmentError` on first function call if not set (not at import time, since the module is imported even in offline mode). Emit a `logger.warning` if called without identity set but `online_tools` is False (shouldn't reach EDGAR anyway).

### Function Signatures (identical to alpha_vantage_fundamentals.py)

```python
def get_balance_sheet(ticker: str, freq: str = 'quarterly', curr_date: str = None) -> str
def get_cashflow(ticker: str, freq: str = 'quarterly', curr_date: str = None) -> str
def get_income_statement(ticker: str, freq: str = 'quarterly', curr_date: str = None) -> str
```

`get_fundamentals` is **not implemented** in this file — it stays on yfinance/alpha_vantage.

### Data Flow

```
ticker + freq + curr_date
  ↓
edgar.set_identity(EDGAR_IDENTITY)
  ↓
form = '10-K' if freq == 'annual' else '10-Q'
  ↓
Company(ticker).get_filings(form=form, date=('2000-01-01', curr_date))
  ↓
filings[0]   ← most recent filing with filing_date ≤ curr_date
  ↓
filing.obj().financials.[income_statement|balance_sheet|cashflow_statement]()
  ↓
statement.to_markdown()   ← LLM-ready markdown table
  ↓
return str
```

### Look-Ahead Bias Prevention

The `date=(start, curr_date)` filter uses the SEC **filing date** — the date the document was publicly filed. This is the correct anchor:

- A 10-K for FY2023 with `period_of_report=2023-09-30` filed on `filing_date=2023-11-03` is NOT visible to a trade algorithm running on `curr_date=2023-10-01`.
- Contrast with yfinance, which uses the fiscal period end date as the column header — requiring the `filter_financials_by_date` post-processing hack to strip future columns.

### Error Handling

| Condition | Exception | Effect in route_to_vendor |
|---|---|---|
| Ticker not found on EDGAR | `SECEdgarNotFoundError(ticker)` | Triggers fallback to alpha_vantage → yfinance |
| No XBRL data in filing | `SECEdgarNoXBRLError(ticker, filing_date)` | Same fallback chain |
| Rate limit / network error | `TooManyRequestsError` (from edgartools) | Retried up to 3x with backoff |
| EDGAR_IDENTITY not set | `EnvironmentError` | Fail fast at startup |

`SECEdgarNotFoundError` and `SECEdgarNoXBRLError` are defined in `sec_edgar_fundamentals.py`. They are caught by `route_to_vendor`'s fallback logic the same way `AlphaVantageRateLimitError` is today.

---

## Optional Cross-Validation Module

### Config

```python
# default_config.py
"validate_financials": False,       # set True to enable cross-validation
"validate_financials_threshold": 0.05,  # 5% deviation triggers warning
```

### Behavior When Enabled

After any SEC EDGAR financial statement call succeeds, the validator:

1. Fetches the same statement from yfinance for the same `ticker` + `curr_date`.
2. Extracts comparable scalar metrics:
   - Income statement: `total_revenue`, `net_income`
   - Balance sheet: `total_assets`, `total_liabilities`
   - Cash flow: `operating_cash_flow`
3. For each metric where both sources have a value: `deviation = |edgar - yfinance| / max(|edgar|, 1)`
4. If `deviation > threshold`: `logger.warning(f"[DataValidation] {ticker} {statement} {metric}: EDGAR={edgar_val} yfinance={yfin_val} deviation={deviation:.1%}")`
5. EDGAR value is always used in the output — validation is informational only.

The validator is implemented as `_validate_financials(ticker, curr_date, statement_type, edgar_result)` in `sec_edgar_fundamentals.py`.

---

## Comprehensive Cross-Source Test Suite

### Location

`tests/test_sec_edgar_vs_yfinance.py` — marked `@pytest.mark.integration` (requires network, slow)

### 50-Stock Universe (10 sectors × 5 tickers)

| Sector | Tickers |
|---|---|
| Technology | AAPL, MSFT, NVDA, GOOGL, META |
| Healthcare | JNJ, UNH, LLY, PFE, ABBV |
| Financials | JPM, BAC, WFC, GS, MS |
| Consumer Discretionary | AMZN, TSLA, HD, MCD, NKE |
| Consumer Staples | PG, KO, PEP, WMT, COST |
| Energy | XOM, CVX, COP, SLB, EOG |
| Industrials | CAT, HON, GE, UNP, RTX |
| Utilities | NEE, DUK, SO, D, AEP |
| Materials | LIN, APD, ECL, DD, NEM |
| Real Estate | AMT, PLD, CCI, EQIX, SPG |

### Test Periods (4 quarters each = up to 200 test cases)

```python
TEST_DATES = [
    "2022-02-15",  # Q1 2022 — post-earnings season
    "2022-08-15",  # Q3 2022 — mid-year
    "2023-02-15",  # Q1 2023
    "2024-02-15",  # Q1 2024
]
```

### Metrics Compared Per Function

| Function | Metrics extracted and compared |
|---|---|
| `get_income_statement` | Total revenue, net income, gross profit, operating income |
| `get_balance_sheet` | Total assets, total liabilities, stockholders equity, cash |
| `get_cashflow` | Operating CF, capex (as negative), free cash flow |

### yfinance Cache

yfinance responses are expensive and flaky to re-fetch. Cache strategy:

- **Cache file:** `tests/data/yfinance_cache.json`
- **Key format:** `"{ticker}_{func}_{freq}_{curr_date}"` (e.g. `"AAPL_income_statement_annual_2024-02-15"`)
- **On test run:** check cache first; only call yfinance if cache miss; write result to cache
- **Cache population script:** `tests/scripts/populate_yfinance_cache.py` — run manually once before running the comparison tests (not part of CI); committed cache is checked in so CI never calls yfinance
- **Cache format:** `{key: {"raw_text": str, "metrics": {metric_name: float}}}` — stores both the raw text and the already-extracted scalar metrics

### Test Assertions

For each (ticker, date, function) triple:

1. **EDGAR call succeeds** — returns non-empty string
2. **yfinance call succeeds** — returns non-empty string (or from cache)
3. **Key metrics extracted** from both
4. **Deviation check** — assert `deviation < 0.15` for at least 3 of 4 metrics (15% threshold for the automated test — stricter than the 5% runtime warning threshold, accounting for legitimate differences in how each source calculates line items)
5. **Result saved** to `tests/data/comparison_report.json` — shows per-ticker deviation stats for analysis

### Test Output

A comparison report `tests/data/edgar_vs_yfinance_report.json` is written after the test run with:

```json
{
  "summary": {"total": 200, "passed": 195, "failed": 5, "avg_deviation_pct": 2.1},
  "by_sector": {"Technology": {"avg_deviation": 1.8, "failures": 0}},
  "failures": [{"ticker": "...", "date": "...", "metric": "...", "edgar": ..., "yfinance": ...}]
}
```

---

## Unit Tests (`test_sec_edgar_fundamentals.py`)

All unit tests mock `edgar.Company` — no network calls.

| Test | What it verifies |
|---|---|
| `test_annual_maps_to_10k` | `freq='annual'` → `form='10-K'` in get_filings call |
| `test_quarterly_maps_to_10q` | `freq='quarterly'` → `form='10-Q'` |
| `test_look_ahead_bias` | `curr_date='2023-10-01'` → filing with `filing_date='2023-11-03'` is excluded |
| `test_not_found_raises` | Empty filings list → `SECEdgarNotFoundError` |
| `test_returns_markdown_string` | Return value is non-empty `str` containing `|` (markdown table) |
| `test_identity_required` | Missing `EDGAR_IDENTITY` env var → `EnvironmentError` |
| `test_validation_warning_on_deviation` | 10% revenue deviation → `logger.warning` called |
| `test_validation_no_warning_within_threshold` | 3% deviation → no warning |

---

## Configuration Changes

### `default_config.py`

```python
# Before
"data_vendors": {
    "fundamental_data": "yfinance",
    ...
}

# After
"data_vendors": {
    "fundamental_data": "sec_edgar",
    ...
}
```

### Environment Variables

| Variable | Required | Example |
|---|---|---|
| `EDGAR_IDENTITY` | Yes (when online_tools=True) | `"TradingAgents user@example.com"` |

Add to `.env.example`.

---

## Dependencies

Add to `pyproject.toml`:

```toml
"edgartools>=5.31.2",
```

---

## Non-Goals

- Replacing `get_fundamentals` (market metrics) — stays on yfinance/alpha_vantage.
- Non-US stocks (SEC EDGAR is US equities only — ADRs may work partially).
- Real-time data — EDGAR filings have a filing lag; the system already accounts for this via `curr_date`.
- Changing agent prompts or output schemas.
