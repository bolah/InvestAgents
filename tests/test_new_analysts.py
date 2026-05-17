# tests/test_new_analysts.py
import pytest


@pytest.mark.unit
def test_create_valuation_analyst_importable():
    from tradingagents.agents.analysts.valuation_analyst import create_valuation_analyst
    assert callable(create_valuation_analyst)


@pytest.mark.unit
def test_create_moat_analyst_importable():
    from tradingagents.agents.analysts.moat_analyst import create_moat_analyst
    assert callable(create_moat_analyst)


@pytest.mark.unit
def test_create_macro_analyst_importable():
    from tradingagents.agents.analysts.macro_analyst import create_macro_analyst
    assert callable(create_macro_analyst)


@pytest.mark.unit
def test_valuation_analyst_node_returns_valuation_report():
    from unittest.mock import MagicMock
    from tradingagents.agents.analysts.valuation_analyst import create_valuation_analyst

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.tool_calls = []
    mock_result.content = "Valuation analysis: P/E is 25x vs 5yr avg 22x."
    mock_llm.bind_tools.return_value.return_value = mock_result

    node = create_valuation_analyst(mock_llm)
    state = {
        "messages": [("human", "AAPL")],
        "company_of_interest": "AAPL",
        "trade_date": "2026-01-01",
        "asset_type": "stock",
    }
    result = node(state)
    assert "valuation_report" in result
    assert result["valuation_report"] == "Valuation analysis: P/E is 25x vs 5yr avg 22x."


@pytest.mark.unit
def test_moat_analyst_node_returns_moat_report():
    from unittest.mock import MagicMock
    from tradingagents.agents.analysts.moat_analyst import create_moat_analyst

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.tool_calls = []
    mock_result.content = "Strong moat via switching costs."
    mock_llm.bind_tools.return_value.return_value = mock_result

    node = create_moat_analyst(mock_llm)
    state = {
        "messages": [("human", "AAPL")],
        "company_of_interest": "AAPL",
        "trade_date": "2026-01-01",
        "asset_type": "stock",
    }
    result = node(state)
    assert "moat_report" in result
    assert result["moat_report"] == "Strong moat via switching costs."


@pytest.mark.unit
def test_macro_analyst_node_returns_macro_report():
    from unittest.mock import MagicMock
    from tradingagents.agents.analysts.macro_analyst import create_macro_analyst

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.tool_calls = []
    mock_result.content = "AI infrastructure tailwind: strong secular growth."
    mock_llm.bind_tools.return_value.return_value = mock_result

    node = create_macro_analyst(mock_llm)
    state = {
        "messages": [("human", "AAPL")],
        "company_of_interest": "AAPL",
        "trade_date": "2026-01-01",
        "asset_type": "stock",
    }
    result = node(state)
    assert "macro_report" in result
    assert result["macro_report"] == "AI infrastructure tailwind: strong secular growth."
