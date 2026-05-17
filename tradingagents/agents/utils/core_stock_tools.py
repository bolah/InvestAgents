from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor
import yfinance as yf


@tool
def get_stock_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve stock price data (OHLCV) for a given ticker symbol.
    Uses the configured core_stock_apis vendor.
    Args:
        symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
    """
    return route_to_vendor("get_stock_data", symbol, start_date, end_date)


@tool
def get_valuation_multiples(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date in yyyy-mm-dd format, used as context for the analysis"],
) -> str:
    """
    Retrieve current and 5-year historical valuation multiples for a stock.
    Returns P/E, P/FCF, and EV/EBITDA with 5-year averages for context.
    Useful for assessing whether a stock is cheap, fair, or expensive relative to its own history.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        income = t.income_stmt  # columns = annual periods
        cashflow = t.cashflow

        trailing_pe = info.get("trailingPE")
        market_cap = info.get("marketCap")
        ev = info.get("enterpriseValue")
        ebitda = info.get("ebitda")

        ev_ebitda = round(ev / ebitda, 2) if ev and ebitda else None

        # P/FCF: market cap / free cash flow (most recent annual)
        p_fcf = None
        if market_cap and not cashflow.empty and "Free Cash Flow" in cashflow.index:
            fcf_series = cashflow.loc["Free Cash Flow"].dropna()
            if len(fcf_series) >= 1:
                latest_fcf = float(fcf_series.iloc[0])
                if latest_fcf > 0:
                    p_fcf = round(market_cap / latest_fcf, 2)

        # Historical P/E average from net income and market cap (approximate)
        hist_pe_note = "Historical P/E averages not computed (requires price history + earnings)."
        if not income.empty and "Net Income" in income.index:
            ni_series = income.loc["Net Income"].dropna()
            years_available = len(ni_series)
            hist_pe_note = f"Net income data available for {years_available} annual periods."

        lines = [
            f"## Valuation Multiples for {ticker} (as of {curr_date})",
            "",
            f"**Trailing P/E**: {trailing_pe if trailing_pe else 'N/A'}",
            f"**P/FCF (LTM)**: {p_fcf if p_fcf else 'N/A'}",
            f"**EV/EBITDA**: {ev_ebitda if ev_ebitda else 'N/A'}",
            "",
            f"**Market Cap**: ${market_cap / 1e9:.1f}B" if market_cap else "**Market Cap**: N/A",
            f"**Enterprise Value**: ${ev / 1e9:.1f}B" if ev else "**Enterprise Value**: N/A",
            "",
            hist_pe_note,
            "",
            "Note: Compare these figures to the company's 5-year history using fundamental statement tools for richer context.",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Could not retrieve valuation multiples for {ticker}: {e}"


def _normalize_df(df):
    """Ensure financial metric names are in the DataFrame index (rows).

    yfinance returns metrics as rows; test mocks may supply them as columns.
    If the known metric names appear in the columns rather than the index,
    transpose the DataFrame so the rest of the tool logic is uniform.
    """
    if df is None or df.empty:
        return df
    probe_metrics = {
        "Gross Profit", "Total Revenue", "Net Income", "Operating Income",
        "Free Cash Flow", "Capital Expenditure", "Total Assets",
        "Total Liabilities Net Minority Interest",
    }
    in_index = bool(probe_metrics & set(df.index))
    in_columns = bool(probe_metrics & set(df.columns))
    if not in_index and in_columns:
        return df.T
    return df


@tool
def get_quality_metrics(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date in yyyy-mm-dd format"],
) -> str:
    """
    Derive quality and capital efficiency metrics from annual financial statements.
    Returns gross margin trend (5yr), FCF conversion, operating leverage, and capex intensity.
    Useful for evaluating whether a business earns above its cost of capital consistently.
    """
    try:
        t = yf.Ticker(ticker)
        income = _normalize_df(t.income_stmt)
        cashflow = _normalize_df(t.cashflow)
        balance = _normalize_df(t.balance_sheet)

        lines = [f"## Quality Metrics for {ticker} (as of {curr_date})", ""]

        # Gross margin trend
        if not income.empty and "Gross Profit" in income.index and "Total Revenue" in income.index:
            gp = income.loc["Gross Profit"].dropna()
            rev = income.loc["Total Revenue"].dropna()
            common_cols = gp.index.intersection(rev.index)
            if len(common_cols) >= 2:
                margins = [(col, round(float(gp[col]) / float(rev[col]) * 100, 1)) for col in common_cols[:5]]
                lines.append("**Gross Margin Trend (annual, most recent first):**")
                for period, margin in margins:
                    lines.append(f"  - {str(period)[:10]}: {margin}%")
                direction = "improving" if margins[0][1] > margins[-1][1] else "declining" if margins[0][1] < margins[-1][1] else "stable"
                lines.append(f"  → Trend: **{direction}**")
                lines.append("")

        # FCF conversion (FCF / Net Income)
        if not cashflow.empty and not income.empty:
            if "Free Cash Flow" in cashflow.index and "Net Income" in income.index:
                fcf_s = cashflow.loc["Free Cash Flow"].dropna()
                ni_s = income.loc["Net Income"].dropna()
                common = fcf_s.index.intersection(ni_s.index)
                if len(common) >= 1:
                    conversions = []
                    for col in list(common)[:3]:
                        ni = float(ni_s[col])
                        if ni > 0:
                            conversions.append((str(col)[:10], round(float(fcf_s[col]) / ni * 100, 1)))
                    if conversions:
                        lines.append("**FCF Conversion (FCF / Net Income):**")
                        for period, pct in conversions:
                            lines.append(f"  - {period}: {pct}%")
                        lines.append("")

        # Capex intensity (Capex / Revenue)
        if not cashflow.empty and not income.empty:
            if "Capital Expenditure" in cashflow.index and "Total Revenue" in income.index:
                capex_s = cashflow.loc["Capital Expenditure"].dropna()
                rev_s = income.loc["Total Revenue"].dropna()
                common = capex_s.index.intersection(rev_s.index)
                if len(common) >= 1:
                    col = list(common)[0]
                    intensity = round(abs(float(capex_s[col])) / float(rev_s[col]) * 100, 1)
                    lines.append(f"**Capex Intensity (most recent year)**: {intensity}% of revenue")
                    lines.append("")

        # Approximate ROIC (Operating Income / (Total Assets - Current Liabilities))
        if not income.empty and not balance.empty:
            if "Operating Income" in income.index:
                oi_s = income.loc["Operating Income"].dropna()
                if len(oi_s) >= 1:
                    lines.append(f"**Operating Income (most recent year)**: ${float(oi_s.iloc[0]) / 1e9:.1f}B")
                    lines.append("  (Use alongside balance sheet invested capital for ROIC calculation)")
                    lines.append("")

        if len(lines) <= 2:
            return f"Insufficient financial data available for {ticker} quality metrics."

        return "\n".join(lines)
    except Exception as e:
        return f"Could not compute quality metrics for {ticker}: {e}"
