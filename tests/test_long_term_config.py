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


@pytest.mark.unit
def test_agent_state_has_new_fields():
    from tradingagents.agents.utils.agent_states import AgentState
    # AgentState is a TypedDict subclass — check its __annotations__
    annotations = AgentState.__annotations__
    assert "investment_horizon" in annotations
    assert "valuation_report" in annotations
    assert "moat_report" in annotations
    assert "macro_report" in annotations


@pytest.mark.unit
def test_propagator_initial_state_has_new_fields():
    from tradingagents.graph.propagation import Propagator
    p = Propagator()
    state = p.create_initial_state("AAPL", "2026-01-01")
    assert state["investment_horizon"] == "3-5 years"
    assert state["valuation_report"] == ""
    assert state["moat_report"] == ""
    assert state["macro_report"] == ""


@pytest.mark.unit
def test_resolve_pending_entries_skipped_when_tracking_disabled(monkeypatch):
    """When outcome_tracking_enabled=False, _resolve_pending_entries must return early."""
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from unittest.mock import MagicMock, patch

    config = {
        **__import__("tradingagents.default_config", fromlist=["DEFAULT_CONFIG"]).DEFAULT_CONFIG,
        "llm_provider": "openai",
        "outcome_tracking_enabled": False,
    }

    with patch("tradingagents.graph.trading_graph.create_llm_client") as mock_llm:
        mock_llm.return_value.get_llm.return_value = MagicMock()
        graph = TradingAgentsGraph(config=config)
        # If guard is in place, _resolve_pending_entries must not call memory_log.get_pending_entries
        graph.memory_log = MagicMock()
        graph._resolve_pending_entries("AAPL")
        graph.memory_log.get_pending_entries.assert_not_called()


@pytest.mark.unit
def test_market_analyst_system_message_is_long_term():
    """Market analyst prompt must not contain short-term trading language."""
    import inspect
    import tradingagents.agents.analysts.market_analyst as m
    src = inspect.getsource(m)
    assert "Technical Signal Analyst" in src
    assert "long-term position" in src
    assert "falling knife" in src
    assert "stop-loss" not in src.lower()


@pytest.mark.unit
def test_fundamentals_analyst_is_long_term():
    import inspect
    import tradingagents.agents.analysts.fundamentals_analyst as f
    src = inspect.getsource(f)
    assert "long-term investor" in src
    assert "past week" not in src
    assert "CAGR" in src or "capital allocation" in src


@pytest.mark.unit
def test_news_analyst_is_long_term():
    import inspect
    import tradingagents.agents.analysts.news_analyst as n
    src = inspect.getsource(n)
    assert "past week" not in src
    assert "traders" not in src
    assert "structural" in src or "long-term" in src
    assert "news_lookback_days" in src


@pytest.mark.unit
def test_sentiment_analyst_is_long_term():
    import inspect
    import tradingagents.agents.analysts.sentiment_analyst as s
    src = inspect.getsource(s)
    assert "_seven_days_back" not in src
    assert "sentiment_lookback_days" in src
    assert "durable narrative" in src or "enduring narrative" in src
    assert "Short-term sentiment" in src
