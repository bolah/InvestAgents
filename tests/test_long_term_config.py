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
