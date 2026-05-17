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
