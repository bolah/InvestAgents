# tests/test_long_term_config.py
import pytest
from tradingagents.default_config import DEFAULT_CONFIG

@pytest.mark.unit
def test_new_config_keys_present():
    assert DEFAULT_CONFIG["investment_horizon"] == "3-5 years"
    assert DEFAULT_CONFIG["news_lookback_days"] == 180
    assert DEFAULT_CONFIG["sentiment_lookback_days"] == 90
    assert DEFAULT_CONFIG["look_back_days"] == 365
    assert DEFAULT_CONFIG["financial_statement_frequency"] == "annual"
    assert DEFAULT_CONFIG["outcome_tracking_enabled"] is False
    assert DEFAULT_CONFIG["holding_days"] == 252
    assert DEFAULT_CONFIG["global_news_lookback_days"] == 180
