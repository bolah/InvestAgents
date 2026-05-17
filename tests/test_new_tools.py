import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


@pytest.mark.unit
def test_get_valuation_multiples_returns_string():
    from tradingagents.agents.utils.core_stock_tools import get_valuation_multiples
    with patch("yfinance.Ticker") as mock_ticker:
        mock_info = {
            "trailingPE": 25.0,
            "marketCap": 3_000_000_000_000,
            "enterpriseValue": 3_100_000_000_000,
            "ebitda": 130_000_000_000,
        }
        mock_income = pd.DataFrame({
            "Net Income": [90e9, 85e9, 80e9, 75e9, 70e9],
            "Total Revenue": [400e9, 380e9, 365e9, 350e9, 340e9],
        })
        mock_cashflow = pd.DataFrame({
            "Free Cash Flow": [100e9, 95e9, 90e9, 85e9, 80e9],
        })
        t = MagicMock()
        t.info = mock_info
        t.income_stmt = mock_income
        t.cashflow = mock_cashflow
        mock_ticker.return_value = t
        result = get_valuation_multiples.func("AAPL", "2026-01-01")
        assert isinstance(result, str)
        assert "P/E" in result or "Valuation" in result


@pytest.mark.unit
def test_get_quality_metrics_returns_string():
    from tradingagents.agents.utils.core_stock_tools import get_quality_metrics
    with patch("yfinance.Ticker") as mock_ticker:
        mock_income = pd.DataFrame({
            "Gross Profit": [170e9, 160e9, 152e9, 143e9, 136e9],
            "Total Revenue": [400e9, 380e9, 365e9, 350e9, 340e9],
            "Net Income": [90e9, 85e9, 80e9, 75e9, 70e9],
            "Operating Income": [120e9, 112e9, 105e9, 98e9, 92e9],
        })
        mock_cashflow = pd.DataFrame({
            "Free Cash Flow": [100e9, 95e9, 90e9, 85e9, 80e9],
            "Capital Expenditure": [-12e9, -11e9, -10e9, -9e9, -8e9],
        })
        mock_balance = pd.DataFrame({
            "Total Assets": [350e9, 330e9, 310e9, 290e9, 275e9],
            "Total Liabilities Net Minority Interest": [280e9, 265e9, 250e9, 235e9, 220e9],
        })
        t = MagicMock()
        t.income_stmt = mock_income
        t.cashflow = mock_cashflow
        t.balance_sheet = mock_balance
        mock_ticker.return_value = t
        result = get_quality_metrics.func("AAPL", "2026-01-01")
        assert isinstance(result, str)
        assert "margin" in result.lower() or "ROIC" in result or "FCF" in result


@pytest.mark.unit
def test_web_search_tool_returns_string_on_ddgs_unavailable():
    """web_search_tool must not raise even if duckduckgo_search is unavailable."""
    import sys
    from unittest.mock import patch
    with patch.dict(sys.modules, {"duckduckgo_search": None}):
        # Re-import to trigger the import failure path
        if "tradingagents.agents.utils.web_tools" in sys.modules:
            del sys.modules["tradingagents.agents.utils.web_tools"]
        from tradingagents.agents.utils.web_tools import web_search_tool
        result = web_search_tool.func("test query")
        assert isinstance(result, str)


@pytest.mark.unit
def test_web_search_tool_returns_formatted_results():
    """web_search_tool returns title + snippet per result when DDGS works."""
    from unittest.mock import patch, MagicMock
    mock_results = [
        {"title": "AI boom drives cloud growth", "body": "Cloud providers see 30% YoY growth..."},
        {"title": "Regulatory scrutiny on big tech", "body": "EU antitrust investigations expand..."},
    ]
    with patch("tradingagents.agents.utils.web_tools.DDGS") as mock_ddgs:
        mock_ddgs.return_value.__enter__.return_value.text.return_value = mock_results
        from tradingagents.agents.utils import web_tools
        import importlib; importlib.reload(web_tools)
        result = web_tools.web_search_tool.func("cloud computing trends 2026", max_results=2)
        assert "AI boom drives cloud growth" in result
        assert "Regulatory scrutiny" in result
