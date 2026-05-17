import logging
import os
from datetime import datetime

import edgar

from tradingagents.dataflows.stockstats_utils import filter_financials_by_date

logger = logging.getLogger(__name__)

_identity_set = False


class SECEdgarNotFoundError(Exception):
    """No EDGAR filings found for ticker before curr_date; triggers vendor fallback."""
    pass


class SECEdgarNoXBRLError(Exception):
    """Filing found but has no parseable XBRL financials; triggers vendor fallback."""
    pass


def _ensure_identity() -> None:
    global _identity_set
    if _identity_set:
        return
    identity = os.environ.get("EDGAR_IDENTITY")
    if not identity:
        from tradingagents.dataflows.config import get_config
        if not get_config().get("online_tools", True):
            logger.warning(
                "EDGAR_IDENTITY is not set; SEC EDGAR calls will fail if online_tools is enabled."
            )
            return
        raise EnvironmentError(
            "EDGAR_IDENTITY environment variable is not set. "
            "Set it to 'AppName your@email.com' per SEC polite-access guidelines."
        )
    edgar.set_identity(identity)
    _identity_set = True


def _get_financials(ticker: str, freq: str, curr_date: str | None) -> tuple:
    """Return (Financials, filing_date, period_of_report) for the most recent filing <= curr_date.

    Uses SEC filing date as the look-ahead anchor: a filing with filing_date=2023-11-03
    is invisible to curr_date=2023-10-01 even if its fiscal period ended 2023-09-30.
    """
    _ensure_identity()
    form = "10-K" if freq.lower() == "annual" else "10-Q"
    end_date = curr_date or datetime.now().strftime("%Y-%m-%d")
    company = edgar.Company(ticker.upper())
    filings = company.get_filings(form=form, date=("2000-01-01", end_date))
    if len(filings) == 0:
        raise SECEdgarNotFoundError(
            f"No {form} filings found for '{ticker}' on or before {end_date}"
        )
    filing = filings[0]  # edgartools returns filings ordered most-recent-first
    obj = filing.obj()
    fin = getattr(obj, "financials", None)
    if fin is None:
        raise SECEdgarNoXBRLError(
            f"No XBRL financials in {form} filing for '{ticker}' "
            f"filed {filing.filing_date}"
        )
    return fin, str(filing.filing_date), str(filing.period_of_report)


def _validate_financials(
    ticker: str,
    curr_date: str,
    statement_type: str,
    fin,
    threshold: float,
) -> None:
    """Compare EDGAR scalar metrics against yfinance; log a warning on deviation > threshold.

    EDGAR values are always used for the actual output — this is informational only.
    Called only when config["validate_financials"] is True.
    """
    import yfinance as yf
    import pandas as pd

    def _yf_scalar(df: pd.DataFrame, *row_names: str) -> float | None:
        for name in row_names:
            if name in df.index:
                val = df.loc[name].iloc[0]
                if pd.notna(val):
                    return float(val)
        return None

    try:
        ticker_obj = yf.Ticker(ticker.upper())
        if statement_type == "income_statement":
            yf_df = filter_financials_by_date(ticker_obj.income_stmt, curr_date)
            comparisons = [
                ("revenue",    fin.get_revenue(),
                 _yf_scalar(yf_df, "Total Revenue", "Revenue")),
                ("net_income", fin.get_net_income(),
                 _yf_scalar(yf_df, "Net Income", "Net Income Common Stockholders")),
            ]
        elif statement_type == "balance_sheet":
            yf_df = filter_financials_by_date(ticker_obj.balance_sheet, curr_date)
            comparisons = [
                ("total_assets",      fin.get_total_assets(),
                 _yf_scalar(yf_df, "Total Assets")),
                ("total_liabilities", fin.get_total_liabilities(),
                 _yf_scalar(yf_df, "Total Liabilities Net Minority Interest",
                            "Total Liabilities")),
            ]
        else:  # cashflow
            yf_df = filter_financials_by_date(ticker_obj.cashflow, curr_date)
            edgar_ocf = fin.get_operating_cash_flow() or fin.get_free_cash_flow()
            comparisons = [
                ("operating_cf", edgar_ocf,
                 _yf_scalar(yf_df, "Operating Cash Flow")),
            ]
    except Exception as exc:
        logger.warning("[DataValidation] %s: could not fetch yfinance data: %s", ticker, exc)
        return

    for metric, edgar_val, yf_val in comparisons:
        if edgar_val is None or yf_val is None:
            continue
        deviation = abs(edgar_val - yf_val) / max(abs(edgar_val), 1.0)
        if deviation > threshold:
            logger.warning(
                "[DataValidation] %s %s %s: EDGAR=%.0f yfinance=%.0f deviation=%.1f%%",
                ticker, statement_type, metric, edgar_val, yf_val, deviation * 100,
            )


def get_income_statement(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    """Get income statement from SEC EDGAR XBRL filing as LLM-ready markdown."""
    from tradingagents.dataflows.config import get_config
    fin, filing_date, period = _get_financials(ticker, freq, curr_date)
    statement = fin.income_statement()
    if statement is None:
        raise SECEdgarNoXBRLError(
            f"Income statement unavailable in EDGAR filing for '{ticker}' "
            f"filed {filing_date}"
        )
    header = (
        f"# Income Statement for {ticker.upper()} ({freq})\n"
        f"# SEC EDGAR filing date: {filing_date} | Period: {period}\n\n"
    )
    result = header + statement.to_markdown()
    config = get_config()
    if config.get("validate_financials"):
        _validate_financials(
            ticker, curr_date, "income_statement", fin,
            config.get("validate_financials_threshold", 0.05),
        )
    return result


def get_balance_sheet(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    """Get balance sheet from SEC EDGAR XBRL filing as LLM-ready markdown."""
    from tradingagents.dataflows.config import get_config
    fin, filing_date, period = _get_financials(ticker, freq, curr_date)
    statement = fin.balance_sheet()
    if statement is None:
        raise SECEdgarNoXBRLError(
            f"Balance sheet unavailable in EDGAR filing for '{ticker}' "
            f"filed {filing_date}"
        )
    header = (
        f"# Balance Sheet for {ticker.upper()} ({freq})\n"
        f"# SEC EDGAR filing date: {filing_date} | Period: {period}\n\n"
    )
    result = header + statement.to_markdown()
    config = get_config()
    if config.get("validate_financials"):
        _validate_financials(
            ticker, curr_date, "balance_sheet", fin,
            config.get("validate_financials_threshold", 0.05),
        )
    return result


def get_cashflow(
    ticker: str, freq: str = "quarterly", curr_date: str | None = None
) -> str:
    """Get cash flow statement from SEC EDGAR XBRL filing as LLM-ready markdown."""
    from tradingagents.dataflows.config import get_config
    fin, filing_date, period = _get_financials(ticker, freq, curr_date)
    statement = fin.cashflow_statement()
    if statement is None:
        raise SECEdgarNoXBRLError(
            f"Cash flow statement unavailable in EDGAR filing for '{ticker}' "
            f"filed {filing_date}"
        )
    header = (
        f"# Cash Flow Statement for {ticker.upper()} ({freq})\n"
        f"# SEC EDGAR filing date: {filing_date} | Period: {period}\n\n"
    )
    result = header + statement.to_markdown()
    config = get_config()
    if config.get("validate_financials"):
        _validate_financials(
            ticker, curr_date, "cashflow", fin,
            config.get("validate_financials_threshold", 0.05),
        )
    return result
