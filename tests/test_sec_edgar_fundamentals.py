"""Unit tests for sec_edgar_fundamentals.py — all mock edgar.Company, no network calls."""

import copy
import logging
import os

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

import tradingagents.default_config as default_config
from tradingagents.dataflows.config import set_config


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_mock_filing(filing_date: str, period: str,
                      income_md: str = "| Revenue | $100 |",
                      balance_md: str = "| Total Assets | $200 |",
                      cashflow_md: str = "| Operating CF | $50 |"):
    """Build a mock Filing → TenK/TenQ → Financials chain."""
    mock_fin = MagicMock()
    mock_fin.income_statement.return_value = MagicMock(
        **{"to_markdown.return_value": income_md}
    )
    mock_fin.balance_sheet.return_value = MagicMock(
        **{"to_markdown.return_value": balance_md}
    )
    mock_fin.cashflow_statement.return_value = MagicMock(
        **{"to_markdown.return_value": cashflow_md}
    )

    mock_obj = MagicMock()
    mock_obj.financials = mock_fin

    mock_filing = MagicMock()
    mock_filing.filing_date = filing_date
    mock_filing.period_of_report = period
    mock_filing.obj.return_value = mock_obj

    return mock_filing, mock_fin


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_identity_flag():
    """Reset module-level identity flag before and after each test."""
    import tradingagents.dataflows.sec_edgar_fundamentals as m
    m._identity_set = False
    yield
    m._identity_set = False


@pytest.fixture(autouse=True)
def _reset_config():
    set_config(copy.deepcopy(default_config.DEFAULT_CONFIG))
    yield
    set_config(copy.deepcopy(default_config.DEFAULT_CONFIG))


# ── mapping tests ─────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestFormMapping:

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    def test_annual_freq_maps_to_10k(self, mock_edgar):
        from tradingagents.dataflows.sec_edgar_fundamentals import get_income_statement
        filing, _ = _make_mock_filing("2023-11-03", "2023-09-30")
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [filing]
        mock_edgar.Company.return_value = mock_company

        get_income_statement("AAPL", freq="annual", curr_date="2024-01-15")

        mock_company.get_filings.assert_called_once_with(
            form="10-K", date=("2000-01-01", "2024-01-15")
        )

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    def test_quarterly_freq_maps_to_10q(self, mock_edgar):
        from tradingagents.dataflows.sec_edgar_fundamentals import get_income_statement
        filing, _ = _make_mock_filing("2023-08-04", "2023-07-01")
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [filing]
        mock_edgar.Company.return_value = mock_company

        get_income_statement("AAPL", freq="quarterly", curr_date="2024-01-15")

        mock_company.get_filings.assert_called_once_with(
            form="10-Q", date=("2000-01-01", "2024-01-15")
        )


# ── look-ahead bias ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestLookAheadBias:

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    def test_curr_date_used_as_range_end(self, mock_edgar):
        """The date-range end must equal curr_date, never today's date."""
        from tradingagents.dataflows.sec_edgar_fundamentals import get_income_statement
        filing, _ = _make_mock_filing("2022-10-28", "2022-09-30")
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [filing]
        mock_edgar.Company.return_value = mock_company

        get_income_statement("AAPL", freq="annual", curr_date="2022-11-01")

        _, kwargs = mock_company.get_filings.call_args
        assert kwargs["date"] == ("2000-01-01", "2022-11-01")

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    def test_filing_after_curr_date_is_excluded(self, mock_edgar):
        """A filing with filing_date=2023-11-03 must NOT be used when curr_date=2023-10-01."""
        from tradingagents.dataflows.sec_edgar_fundamentals import get_income_statement, SECEdgarNotFoundError
        # edgartools filters by date; simulated here by returning empty list
        mock_company = MagicMock()
        mock_company.get_filings.return_value = []  # as if no filing exists before curr_date
        mock_edgar.Company.return_value = mock_company

        with pytest.raises(SECEdgarNotFoundError):
            get_income_statement("AAPL", freq="annual", curr_date="2023-10-01")

        # confirm date range end is curr_date, not some future date
        _, kwargs = mock_company.get_filings.call_args
        assert kwargs["date"][1] == "2023-10-01"


# ── error handling ────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestErrorHandling:

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    def test_empty_filings_raises_not_found(self, mock_edgar):
        from tradingagents.dataflows.sec_edgar_fundamentals import (
            get_income_statement, SECEdgarNotFoundError,
        )
        mock_company = MagicMock()
        mock_company.get_filings.return_value = []
        mock_edgar.Company.return_value = mock_company

        with pytest.raises(SECEdgarNotFoundError, match="ZZZZZ"):
            get_income_statement("ZZZZZ", freq="annual", curr_date="2024-01-15")

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    def test_none_financials_raises_no_xbrl(self, mock_edgar):
        from tradingagents.dataflows.sec_edgar_fundamentals import (
            get_income_statement, SECEdgarNoXBRLError,
        )
        obj = MagicMock()
        obj.financials = None
        filing = MagicMock()
        filing.filing_date = "2023-11-03"
        filing.period_of_report = "2023-09-30"
        filing.obj.return_value = obj
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [filing]
        mock_edgar.Company.return_value = mock_company

        with pytest.raises(SECEdgarNoXBRLError):
            get_income_statement("AAPL", freq="annual", curr_date="2024-01-15")

    def test_missing_edgar_identity_raises_environment_error(self, monkeypatch):
        monkeypatch.delenv("EDGAR_IDENTITY", raising=False)
        import tradingagents.dataflows.sec_edgar_fundamentals as m
        m._identity_set = False

        from tradingagents.dataflows.sec_edgar_fundamentals import get_income_statement
        with pytest.raises(EnvironmentError, match="EDGAR_IDENTITY"):
            get_income_statement("AAPL", freq="annual", curr_date="2024-01-15")


# ── return value ──────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestReturnFormat:

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    def test_income_statement_returns_markdown_string(self, mock_edgar):
        from tradingagents.dataflows.sec_edgar_fundamentals import get_income_statement
        filing, _ = _make_mock_filing("2023-11-03", "2023-09-30",
                                       income_md="| Net Revenue | $383,285 |")
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [filing]
        mock_edgar.Company.return_value = mock_company

        result = get_income_statement("AAPL", freq="annual", curr_date="2024-01-15")

        assert isinstance(result, str)
        assert "|" in result
        assert "AAPL" in result

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    def test_balance_sheet_returns_markdown_string(self, mock_edgar):
        from tradingagents.dataflows.sec_edgar_fundamentals import get_balance_sheet
        filing, _ = _make_mock_filing("2023-11-03", "2023-09-30",
                                       balance_md="| Total Assets | $352,583 |")
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [filing]
        mock_edgar.Company.return_value = mock_company

        result = get_balance_sheet("AAPL", freq="annual", curr_date="2024-01-15")

        assert isinstance(result, str)
        assert "|" in result

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    def test_cashflow_returns_markdown_string(self, mock_edgar):
        from tradingagents.dataflows.sec_edgar_fundamentals import get_cashflow
        filing, _ = _make_mock_filing("2023-11-03", "2023-09-30",
                                       cashflow_md="| Operating CF | $110,543 |")
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [filing]
        mock_edgar.Company.return_value = mock_company

        result = get_cashflow("AAPL", freq="annual", curr_date="2024-01-15")

        assert isinstance(result, str)
        assert "|" in result

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    def test_result_contains_filing_date_header(self, mock_edgar):
        """The header must include the filing date so the LLM knows data provenance."""
        from tradingagents.dataflows.sec_edgar_fundamentals import get_income_statement
        filing, _ = _make_mock_filing("2023-11-03", "2023-09-30")
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [filing]
        mock_edgar.Company.return_value = mock_company

        result = get_income_statement("AAPL", freq="annual", curr_date="2024-01-15")

        assert "2023-11-03" in result  # filing_date in header


# ── validation ────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestValidationFlag:

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    @patch("tradingagents.dataflows.sec_edgar_fundamentals._validate_financials")
    def test_validation_called_when_flag_enabled(self, mock_validate, mock_edgar):
        from tradingagents.dataflows.sec_edgar_fundamentals import get_income_statement
        filing, _ = _make_mock_filing("2023-11-03", "2023-09-30")
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [filing]
        mock_edgar.Company.return_value = mock_company

        set_config({
            **copy.deepcopy(default_config.DEFAULT_CONFIG),
            "validate_financials": True,
        })
        get_income_statement("AAPL", freq="annual", curr_date="2024-01-15")

        mock_validate.assert_called_once()

    @patch("tradingagents.dataflows.sec_edgar_fundamentals.edgar")
    @patch("tradingagents.dataflows.sec_edgar_fundamentals._validate_financials")
    def test_validation_not_called_when_flag_disabled(self, mock_validate, mock_edgar):
        from tradingagents.dataflows.sec_edgar_fundamentals import get_income_statement
        filing, _ = _make_mock_filing("2023-11-03", "2023-09-30")
        mock_company = MagicMock()
        mock_company.get_filings.return_value = [filing]
        mock_edgar.Company.return_value = mock_company

        # default config has validate_financials: False
        get_income_statement("AAPL", freq="annual", curr_date="2024-01-15")

        mock_validate.assert_not_called()


@pytest.mark.unit
class TestValidationWarnings:

    def _make_income_df(self, revenue: float, net_income: float) -> pd.DataFrame:
        df = pd.DataFrame({
            pd.Timestamp("2023-09-30"): {
                "Total Revenue": revenue,
                "Net Income": net_income,
            }
        }).T
        return df

    @patch("yfinance.Ticker")
    def test_warns_on_revenue_deviation_above_threshold(self, mock_ticker_cls, caplog):
        """10% revenue deviation triggers a DataValidation warning."""
        from tradingagents.dataflows.sec_edgar_fundamentals import _validate_financials

        mock_fin = MagicMock()
        mock_fin.get_revenue.return_value = 100_000_000_000.0   # EDGAR: $100B
        mock_fin.get_net_income.return_value = 20_000_000_000.0

        mock_ticker = MagicMock()
        mock_ticker.income_stmt = self._make_income_df(110_000_000_000.0, 21_000_000_000.0)
        mock_ticker_cls.return_value = mock_ticker

        with caplog.at_level(logging.WARNING, logger="tradingagents.dataflows.sec_edgar_fundamentals"):
            _validate_financials("FAKE", "2024-01-15", "income_statement", mock_fin, threshold=0.05)

        assert "[DataValidation]" in caplog.text
        assert "revenue" in caplog.text

    @patch("yfinance.Ticker")
    def test_no_warning_when_deviation_below_threshold(self, mock_ticker_cls, caplog):
        """3% deviation (below 5% threshold) must not produce a warning."""
        from tradingagents.dataflows.sec_edgar_fundamentals import _validate_financials

        mock_fin = MagicMock()
        mock_fin.get_revenue.return_value = 100_000_000_000.0
        mock_fin.get_net_income.return_value = 20_000_000_000.0

        mock_ticker = MagicMock()
        mock_ticker.income_stmt = self._make_income_df(103_000_000_000.0, 20_500_000_000.0)
        mock_ticker_cls.return_value = mock_ticker

        with caplog.at_level(logging.WARNING, logger="tradingagents.dataflows.sec_edgar_fundamentals"):
            _validate_financials("FAKE", "2024-01-15", "income_statement", mock_fin, threshold=0.05)

        assert "[DataValidation]" not in caplog.text
