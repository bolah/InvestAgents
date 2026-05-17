# Long-Term Investment System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform InvestAgents from a short-term trading system (7-day lookbacks, stop-loss schemas) into a 3-5 year investment analysis system with three new analyst roles and long-term-tuned prompts throughout.

**Architecture:** Surgical in-place rewrite — LangGraph graph topology is preserved. Phases work through the stack bottom-up: config → state → schemas → existing analysts → new analysts → debate agents → CLI.

**Tech Stack:** LangGraph, LangChain, Pydantic v2, yfinance, duckduckgo-search (new), questionary, Rich

---

## File Map

**Modified:**
- `tradingagents/default_config.py` — new config keys (7 additions, 1 update)
- `tradingagents/agents/utils/agent_states.py` — 4 new AgentState fields
- `tradingagents/graph/propagation.py` — add new fields to initial state
- `tradingagents/agents/schemas.py` — rename TraderProposal→InvestmentProposal, update PortfolioDecision + ResearchPlan
- `tradingagents/agents/trader/trader.py` — import rename
- `tradingagents/graph/trading_graph.py` — reflection guard + 3 new tool nodes + import
- `tradingagents/graph/setup.py` — 3 new analyst factories
- `tradingagents/graph/conditional_logic.py` — 3 new `should_continue_*` methods
- `tradingagents/agents/__init__.py` — 3 new analyst imports + __all__ entries
- `tradingagents/agents/analysts/market_analyst.py` — system prompt rewrite
- `tradingagents/agents/analysts/fundamentals_analyst.py` — system prompt rewrite
- `tradingagents/agents/analysts/news_analyst.py` — lookback + system prompt rewrite
- `tradingagents/agents/analysts/sentiment_analyst.py` — lookback + system prompt rewrite
- `tradingagents/agents/utils/core_stock_tools.py` — 2 new tools
- `tradingagents/agents/researchers/bull_researcher.py` — horizon context + new reports
- `tradingagents/agents/researchers/bear_researcher.py` — horizon context + new reports
- `tradingagents/agents/risk_mgmt/aggressive_debator.py` — horizon context
- `tradingagents/agents/risk_mgmt/conservative_debator.py` — horizon context
- `tradingagents/agents/risk_mgmt/neutral_debator.py` — horizon context
- `tradingagents/agents/managers/portfolio_manager.py` — horizon context
- `cli/models.py` — 3 new AnalystType enum values
- `cli/utils.py` — 3 new ANALYST_ORDER entries
- `cli/main.py` — investment horizon wizard step + wire to config
- `pyproject.toml` — add duckduckgo-search dependency
- `tests/test_structured_agents.py` — update TraderProposal → InvestmentProposal references

**Created:**
- `tradingagents/agents/utils/web_tools.py` — web_search_tool wrapping duckduckgo-search
- `tradingagents/agents/analysts/valuation_analyst.py` — valuation multiples analyst
- `tradingagents/agents/analysts/moat_analyst.py` — economic moat / quality analyst
- `tradingagents/agents/analysts/macro_analyst.py` — macro/secular trends analyst

---

## Task 1: Add duckduckgo-search dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dependency**

In `pyproject.toml`, add `"duckduckgo-search>=6.2.0",` to the `dependencies` list after the existing entries:

```toml
    "yfinance>=0.2.63",
    "duckduckgo-search>=6.2.0",
```

- [ ] **Step 2: Sync dependencies**

```bash
uv sync
```

Expected: package installs without error. Verify: `python -c "from duckduckgo_search import DDGS; print('ok')"` prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add duckduckgo-search dependency for macro analyst web search"
```

---

## Task 2: Configuration layer

**Files:**
- Modify: `tradingagents/default_config.py`

- [ ] **Step 1: Write failing test**

```python
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_long_term_config.py -v
```

Expected: `FAILED` — `KeyError: 'investment_horizon'`

- [ ] **Step 3: Add config keys to default_config.py**

In `tradingagents/default_config.py`, add inside the `_apply_env_overrides({...})` dict, after the `"global_news_article_limit"` line (line 82):

```python
    # Long-term investment configuration
    "investment_horizon": "3-5 years",
    "news_lookback_days": 180,
    "sentiment_lookback_days": 90,
    "look_back_days": 365,
    "financial_statement_frequency": "annual",
    "outcome_tracking_enabled": False,
    "holding_days": 252,
```

Also update line 83 (current `"global_news_lookback_days": 7`) to:

```python
    "global_news_lookback_days": 180,
```

- [ ] **Step 4: Run test**

```bash
pytest tests/test_long_term_config.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tradingagents/default_config.py tests/test_long_term_config.py
git commit -m "feat(config): add long-term investment config keys"
```

---

## Task 3: Extend AgentState with new report fields

**Files:**
- Modify: `tradingagents/agents/utils/agent_states.py`

- [ ] **Step 1: Write failing test**

```python
# in tests/test_long_term_config.py — append to existing file

@pytest.mark.unit
def test_agent_state_has_new_fields():
    from tradingagents.agents.utils.agent_states import AgentState
    # AgentState is a TypedDict subclass — check its __annotations__
    annotations = AgentState.__annotations__
    assert "investment_horizon" in annotations
    assert "valuation_report" in annotations
    assert "moat_report" in annotations
    assert "macro_report" in annotations
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_long_term_config.py::test_agent_state_has_new_fields -v
```

Expected: `FAILED` — `AssertionError: assert 'investment_horizon' in ...`

- [ ] **Step 3: Add fields to AgentState**

In `tradingagents/agents/utils/agent_states.py`, after the `past_context` field (last line of `AgentState`):

```python
    past_context: Annotated[str, "Memory log context injected at run start (same-ticker decisions + cross-ticker lessons)"]

    # Long-term investment fields
    investment_horizon: Annotated[str, "Investment horizon, e.g. '3-5 years'"]
    valuation_report: Annotated[str, "Report from the Valuation Analyst"]
    moat_report: Annotated[str, "Report from the Moat/Quality Analyst"]
    macro_report: Annotated[str, "Report from the Macro/Secular Analyst"]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_long_term_config.py -v
```

Expected: both tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tradingagents/agents/utils/agent_states.py tests/test_long_term_config.py
git commit -m "feat(state): add investment_horizon, valuation_report, moat_report, macro_report to AgentState"
```

---

## Task 4: Propagation — initialize new state fields

**Files:**
- Modify: `tradingagents/graph/propagation.py`

- [ ] **Step 1: Write failing test**

```python
# in tests/test_long_term_config.py — append

@pytest.mark.unit
def test_propagator_initial_state_has_new_fields():
    from tradingagents.graph.propagation import Propagator
    p = Propagator()
    state = p.create_initial_state("AAPL", "2026-01-01")
    assert state["investment_horizon"] == "3-5 years"
    assert state["valuation_report"] == ""
    assert state["moat_report"] == ""
    assert state["macro_report"] == ""
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_long_term_config.py::test_propagator_initial_state_has_new_fields -v
```

Expected: `FAILED` — `KeyError: 'investment_horizon'`

- [ ] **Step 3: Update create_initial_state in propagation.py**

Change the signature to accept `investment_horizon`:

```python
def create_initial_state(
    self,
    company_name: str,
    trade_date: str,
    asset_type: str = "stock",
    past_context: str = "",
    investment_horizon: str = "3-5 years",
) -> Dict[str, Any]:
```

Add the new fields to the returned dict (after `"news_report": ""`):

```python
            "news_report": "",
            "investment_horizon": investment_horizon,
            "valuation_report": "",
            "moat_report": "",
            "macro_report": "",
```

- [ ] **Step 4: Update call site in trading_graph.py**

In `tradingagents/graph/trading_graph.py`, in `_run_graph()` (around line 337), update the `create_initial_state` call to pass `investment_horizon` from config:

```python
        init_agent_state = self.propagator.create_initial_state(
            company_name,
            trade_date,
            past_context=past_context,
            investment_horizon=self.config.get("investment_horizon", "3-5 years"),
        )
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_long_term_config.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 6: Run full suite to check for regressions**

```bash
pytest -m unit
```

Expected: all `PASSED`

- [ ] **Step 7: Commit**

```bash
git add tradingagents/graph/propagation.py tradingagents/graph/trading_graph.py tests/test_long_term_config.py
git commit -m "feat(propagation): initialize investment_horizon and new report fields in state"
```

---

## Task 5: Schema changes — InvestmentProposal + PortfolioDecision + ResearchPlan

**Files:**
- Modify: `tradingagents/agents/schemas.py`
- Modify: `tradingagents/agents/trader/trader.py`
- Modify: `tests/test_structured_agents.py`

- [ ] **Step 1: Update failing tests in test_structured_agents.py**

Replace `TraderProposal` and `TraderAction` imports with `InvestmentProposal` (keeping `TraderAction` since the enum stays). Replace all `TraderProposal(...)` usages with `InvestmentProposal(...)`. Update field tests to use `conviction_score`, `thesis_horizon`, `key_catalysts` instead of `entry_price`, `stop_loss`.

Change the import block at the top of `tests/test_structured_agents.py`:

```python
from tradingagents.agents.schemas import (
    PortfolioRating,
    ResearchPlan,
    TraderAction,
    InvestmentProposal,
    render_research_plan,
    render_trader_proposal,
)
```

Replace the `TestRenderTraderProposal` class:

```python
@pytest.mark.unit
class TestRenderTraderProposal:
    def test_minimal_required_fields(self):
        p = InvestmentProposal(
            action=TraderAction.HOLD,
            reasoning="Balanced setup; no edge.",
            conviction_score=5,
            thesis_horizon="3-5 years",
            key_catalysts="1. Earnings growth. 2. Margin expansion.",
        )
        md = render_trader_proposal(p)
        assert "**Action**: Hold" in md
        assert "**Reasoning**: Balanced setup; no edge." in md
        assert "**Conviction Score**: 5" in md
        assert "**Thesis Horizon**: 3-5 years" in md
        assert "FINAL TRANSACTION PROPOSAL: **HOLD**" in md

    def test_all_fields_rendered(self):
        p = InvestmentProposal(
            action=TraderAction.BUY,
            reasoning="Strong moat and valuation.",
            conviction_score=8,
            thesis_horizon="5 years",
            key_catalysts="1. Cloud growth. 2. AI monetization.",
            position_sizing="5% of portfolio",
        )
        md = render_trader_proposal(p)
        assert "**Action**: Buy" in md
        assert "**Conviction Score**: 8" in md
        assert "**Thesis Horizon**: 5 years" in md
        assert "**Key Catalysts**: 1. Cloud growth" in md
        assert "**Position Sizing**: 5% of portfolio" in md
        assert "FINAL TRANSACTION PROPOSAL: **BUY**" in md

    def test_no_entry_price_or_stop_loss_fields(self):
        p = InvestmentProposal(
            action=TraderAction.SELL,
            reasoning="Structural decline.",
            conviction_score=7,
            thesis_horizon="2 years",
            key_catalysts="1. Margin compression. 2. Market share loss.",
        )
        md = render_trader_proposal(p)
        assert "Entry Price" not in md
        assert "Stop Loss" not in md
```

- [ ] **Step 2: Run to verify tests fail**

```bash
pytest tests/test_structured_agents.py -v
```

Expected: `FAILED` — `ImportError: cannot import name 'InvestmentProposal'`

- [ ] **Step 3: Rename TraderProposal → InvestmentProposal in schemas.py**

In `tradingagents/agents/schemas.py`:

Replace the `TraderProposal` class (lines 109–138) with:

```python
class InvestmentProposal(BaseModel):
    """Structured transaction proposal produced by the Trader for a long-term investment horizon.

    The trader reads the Research Manager's investment plan and the analyst
    reports, then produces a concrete transaction: what action to take,
    the conviction behind it, the thesis horizon, and the catalysts to watch.
    """

    action: TraderAction = Field(
        description="The transaction direction. Exactly one of Buy / Hold / Sell.",
    )
    reasoning: str = Field(
        description=(
            "The case for this action, anchored in the analysts' reports and "
            "the research plan. Two to four sentences."
        ),
    )
    conviction_score: int = Field(
        description=(
            "Conviction level 1-10. 7+ = meaningful position size. "
            "Below 5 = insufficient clarity to invest."
        ),
    )
    thesis_horizon: str = Field(
        description="Expected timeframe for thesis to play out, e.g. '3-5 years'.",
    )
    key_catalysts: str = Field(
        description=(
            "2-3 concrete milestones or events that would validate or invalidate "
            "the thesis. Be specific."
        ),
    )
    position_sizing: Optional[str] = Field(
        default=None,
        description="Optional sizing guidance, e.g. '5% of portfolio'.",
    )
```

Replace `render_trader_proposal` (lines 141–163):

```python
def render_trader_proposal(proposal: InvestmentProposal) -> str:
    """Render an InvestmentProposal to markdown.

    The trailing ``FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**`` line is
    preserved for backward compatibility with the analyst stop-signal text
    and any external code that greps for it.
    """
    parts = [
        f"**Action**: {proposal.action.value}",
        "",
        f"**Reasoning**: {proposal.reasoning}",
        "",
        f"**Conviction Score**: {proposal.conviction_score}/10",
        "",
        f"**Thesis Horizon**: {proposal.thesis_horizon}",
        "",
        f"**Key Catalysts**: {proposal.key_catalysts}",
    ]
    if proposal.position_sizing:
        parts.extend(["", f"**Position Sizing**: {proposal.position_sizing}"])
    parts.extend([
        "",
        f"FINAL TRANSACTION PROPOSAL: **{proposal.action.value.upper()}**",
    ])
    return "\n".join(parts)
```

Update `PortfolioDecision.executive_summary` description (around line 187):

```python
    executive_summary: str = Field(
        description=(
            "A concise action plan covering investment thesis, conviction level, "
            "expected catalysts, and holding horizon. Two to four sentences."
        ),
    )
```

Update `PortfolioDecision.time_horizon` (around line 203): change from `Optional[str]` to `str` (required) and update description:

```python
    time_horizon: str = Field(
        description="Recommended holding period, e.g. '3-5 years'.",
    )
```

Update `ResearchPlan.strategic_actions` description (around line 85):

```python
    strategic_actions: str = Field(
        description=(
            "Concrete steps for the **investor** to implement the recommendation, "
            "including position sizing guidance consistent with the rating."
        ),
    )
```

- [ ] **Step 4: Update trader.py import**

In `tradingagents/agents/trader/trader.py`, change line 9:

```python
from tradingagents.agents.schemas import InvestmentProposal, render_trader_proposal
```

Change line 21:

```python
    structured_llm = bind_structured(llm, InvestmentProposal, "Trader")
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_structured_agents.py -v
```

Expected: `PASSED`

- [ ] **Step 6: Run full unit suite**

```bash
pytest -m unit
```

Expected: all `PASSED`

- [ ] **Step 7: Commit**

```bash
git add tradingagents/agents/schemas.py tradingagents/agents/trader/trader.py tests/test_structured_agents.py
git commit -m "feat(schemas): rename TraderProposal to InvestmentProposal with long-term conviction fields"
```

---

## Task 6: Guard reflection — disable outcome tracking

**Files:**
- Modify: `tradingagents/graph/trading_graph.py`

- [ ] **Step 1: Write test**

```python
# in tests/test_long_term_config.py — append

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
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_long_term_config.py::test_resolve_pending_entries_skipped_when_tracking_disabled -v
```

Expected: `FAILED` — `AssertionError: Expected 'get_pending_entries' to not have been called`

- [ ] **Step 3: Add guard to _resolve_pending_entries in trading_graph.py**

At the very top of the `_resolve_pending_entries` method body (line 255 area), add:

```python
    def _resolve_pending_entries(self, ticker: str) -> None:
        if not self.config.get("outcome_tracking_enabled", False):
            return
        # ... rest of existing method unchanged
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_long_term_config.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tradingagents/graph/trading_graph.py tests/test_long_term_config.py
git commit -m "feat(reflection): guard _resolve_pending_entries behind outcome_tracking_enabled flag"
```

---

## Task 7: Market Analyst — reframe as Technical Signal Analyst

**Files:**
- Modify: `tradingagents/agents/analysts/market_analyst.py`

- [ ] **Step 1: Write test**

```python
# in tests/test_long_term_config.py — append

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
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_long_term_config.py::test_market_analyst_system_message_is_long_term -v
```

Expected: `FAILED`

- [ ] **Step 3: Replace system_message in market_analyst.py**

Replace the `system_message` variable (lines 25–52) in `create_market_analyst`:

```python
        system_message = (
            """You are a Technical Signal Analyst evaluating whether the current price structure is appropriate for initiating a long-term (3-5 year) position.

Your role is NOT to predict short-term price moves. Your role is to identify:
1. Whether the stock is in a structural downtrend that would make entry dangerous ("falling knife" risk).
2. Whether the current price level is a reasonable entry relative to its long-term trend and 52-week range.

Available indicators — select up to 8 that are complementary and non-redundant:

Moving Averages (primary signals for long-term analysis):
- close_50_sma: 50 SMA — medium-term trend. Is price above or below? Is price approaching or departing from this level?
- close_200_sma: 200 SMA — long-term trend benchmark. A price consistently below the 200 SMA signals structural weakness.
- close_10_ema: 10 EMA — short-term momentum. Use only to detect acceleration or deceleration of a trend.

MACD:
- macd, macds, macdh: Momentum and trend change signals. **These carry low weight for multi-year decisions. Only flag if they indicate a severe downtrend that would make entry timing significantly worse.**

Momentum:
- rsi: RSI — **Low weight for multi-year decisions.** Only flag if deeply oversold (<25) as a potential capitulation signal, or if extremely overbought (>80) suggesting near-term overshoot.

Volatility:
- boll, boll_ub, boll_lb: Bollinger Bands — assess whether price is extended relative to recent volatility.
- atr: ATR — volatility context only. Do NOT use for stop-loss guidance.

Volume:
- vwma: VWMA — volume confirmation of trend direction.

Instructions:
- Call get_stock_data first, then get_indicators with specific indicator names.
- Emphasize: 52-week range position, proximity to 200-SMA, and whether the trend structure is bullish, neutral, or in structural decline.
- Conclude with: "Is the current technical picture consistent with initiating a long-term position?" Answer clearly: Yes / Cautious Yes / No — and why.
- Write a detailed report with a Markdown summary table at the end."""
            + get_language_instruction()
        )
```

Also update the ATR description in the prompt: the original says "Usage: Set stop-loss levels" — this is now removed as it's been replaced in full.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_long_term_config.py::test_market_analyst_system_message_is_long_term -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tradingagents/agents/analysts/market_analyst.py tests/test_long_term_config.py
git commit -m "feat(analysts): reframe market analyst as Technical Signal Analyst for long-term entry evaluation"
```

---

## Task 8: Fundamentals Analyst — long-term framing

**Files:**
- Modify: `tradingagents/agents/analysts/fundamentals_analyst.py`

- [ ] **Step 1: Write test**

```python
# in tests/test_long_term_config.py — append

@pytest.mark.unit
def test_fundamentals_analyst_is_long_term():
    import inspect
    import tradingagents.agents.analysts.fundamentals_analyst as f
    src = inspect.getsource(f)
    assert "long-term investor" in src
    assert "past week" not in src
    assert "CAGR" in src or "capital allocation" in src
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_long_term_config.py::test_fundamentals_analyst_is_long_term -v
```

Expected: `FAILED`

- [ ] **Step 3: Replace system_message in fundamentals_analyst.py**

Replace the `system_message` variable (line 27 area):

```python
        system_message = (
            "You are a fundamental analysis researcher tasked with evaluating a company's long-term investment quality. "
            "Your audience is a long-term investor with a 3-5 year horizon — not a trader. "
            "Write a comprehensive report covering: "
            "(1) Revenue CAGR over the past 5 years and the quality of that growth (organic vs. acquisitions); "
            "(2) Gross margin trend — improving, stable, or deteriorating; "
            "(3) Operating leverage — does revenue growth translate to faster earnings growth?; "
            "(4) Capital allocation quality — share buybacks vs. dilution, FCF reinvestment discipline, dividend sustainability; "
            "(5) Balance sheet durability — net debt/EBITDA, interest coverage, liquidity runway; "
            "(6) Management track record on guidance and capital deployment. "
            "Use annual financial statements for all multi-year trend analysis. "
            "Provide specific, evidence-based insights to help long-term investors assess business quality and durability."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            + " Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, `get_cashflow`, and `get_income_statement` for specific financial statements."
            + get_language_instruction()
        )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_long_term_config.py::test_fundamentals_analyst_is_long_term -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tradingagents/agents/analysts/fundamentals_analyst.py tests/test_long_term_config.py
git commit -m "feat(analysts): reframe fundamentals analyst for long-term investor audience"
```

---

## Task 9: News Analyst — extend lookback and reframe

**Files:**
- Modify: `tradingagents/agents/analysts/news_analyst.py`

- [ ] **Step 1: Write test**

```python
# in tests/test_long_term_config.py — append

@pytest.mark.unit
def test_news_analyst_is_long_term():
    import inspect
    import tradingagents.agents.analysts.news_analyst as n
    src = inspect.getsource(n)
    assert "past week" not in src
    assert "traders" not in src
    assert "structural" in src or "long-term" in src
    assert "news_lookback_days" in src
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_long_term_config.py::test_news_analyst_is_long_term -v
```

Expected: `FAILED`

- [ ] **Step 3: Rewrite news_analyst.py**

Replace the entire `system_message` string and add lookback config reading:

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_global_news,
    get_language_instruction,
    get_news,
)
from tradingagents.dataflows.config import get_config


def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        asset_type = state.get("asset_type", "stock")
        asset_label = "company" if asset_type == "stock" else "asset"
        instrument_context = build_instrument_context(
            state["company_of_interest"], asset_type
        )
        config = get_config()
        lookback_days = config.get("news_lookback_days", 180)

        tools = [
            get_news,
            get_global_news,
        ]

        system_message = (
            f"You are a structural news researcher evaluating events and trends relevant to a long-term (3-5 year) investment in this {asset_label}. "
            f"Use get_news for {asset_label}-specific news searches and get_global_news for macroeconomic context. "
            f"Use a lookback window of approximately {lookback_days} days. "
            "Focus exclusively on structural, durable signals: "
            "(1) Regulatory shifts or legal developments that could affect the business model; "
            "(2) Competitive disruptions — new entrants, M&A activity, product obsolescence risks; "
            "(3) Macro tailwinds or headwinds — interest rate sensitivity, commodity exposure, geopolitical exposure; "
            "(4) Management changes — CEO/CFO turnover, board composition, insider buying or selling patterns; "
            "(5) Capital structure events — large acquisitions, spin-offs, major debt issuances. "
            "Do NOT report on: day-to-day price moves, short-term earnings beats/misses, analyst upgrades/downgrades unless they reflect a thesis change. "
            "Frame every finding in terms of: does this change the 3-5 year outlook for this business? "
            "Provide a comprehensive narrative report with a Markdown summary table at the end."
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "news_report": report,
        }

    return news_analyst_node
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_long_term_config.py::test_news_analyst_is_long_term -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tradingagents/agents/analysts/news_analyst.py tests/test_long_term_config.py
git commit -m "feat(analysts): reframe news analyst for structural 3-5yr trends with configurable lookback"
```

---

## Task 10: Sentiment Analyst — narrative reframe and configurable lookback

**Files:**
- Modify: `tradingagents/agents/analysts/sentiment_analyst.py`

- [ ] **Step 1: Write test**

```python
# in tests/test_long_term_config.py — append

@pytest.mark.unit
def test_sentiment_analyst_is_long_term():
    import inspect
    import tradingagents.agents.analysts.sentiment_analyst as s
    src = inspect.getsource(s)
    assert "_seven_days_back" not in src
    assert "sentiment_lookback_days" in src
    assert "durable narrative" in src or "enduring narrative" in src
    assert "Short-term sentiment" in src
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_long_term_config.py::test_sentiment_analyst_is_long_term -v
```

Expected: `FAILED`

- [ ] **Step 3: Update sentiment_analyst.py**

Replace `_seven_days_back` helper with a config-based helper and update `_build_system_message`:

At the top, add import:

```python
from tradingagents.dataflows.config import get_config
```

Replace lines 34–35 (`_seven_days_back` function):

```python
def _lookback_start(trade_date: str, days: int) -> str:
    return (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")
```

Update `sentiment_analyst_node` lines 47–49:

```python
        end_date = state["trade_date"]
        config = get_config()
        lookback_days = config.get("sentiment_lookback_days", 90)
        start_date = _lookback_start(end_date, lookback_days)
```

In `_build_system_message`, update the function signature to remove the implicit 7-day label and rewrite the prompt:

Replace the entire string returned by `_build_system_message`:

```python
def _build_system_message(
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    news_block: str,
    stocktwits_block: str,
    reddit_block: str,
) -> str:
    """Assemble the stakeholder-narrative system message with structured data blocks."""
    return f"""You are a Stakeholder & Narrative Analyst. Your task is to identify the **enduring narrative** the market has about {ticker} and whether that narrative is shifting — using three pre-fetched data sources covering {start_date} to {end_date}.

Short-term sentiment fluctuations (single-day reactions, earnings beats/misses) are noise at a 3-5 year investment horizon. Focus only on durable narrative changes that could affect long-term positioning.

## Data sources (pre-fetched)

### News headlines — Yahoo Finance
Institutional framing. What themes keep recurring? What has changed structurally?

<start_of_news>
{news_block}
<end_of_news>

### StockTwits messages — retail-trader sentiment
Each message carries a user-labeled tag (Bullish / Bearish / no-label).

<start_of_stocktwits>
{stocktwits_block}
<end_of_stocktwits>

### Reddit posts — r/wallstreetbets, r/stocks, r/investing
Community discussion. Engagement via upvote score and comment count matters.

<start_of_reddit>
{reddit_block}
<end_of_reddit>

## What to look for

1. **Dominant narrative**: What is the prevailing long-term story the market tells about this company? (e.g., "AI infrastructure winner", "legacy tech disruption risk", "reliable compounder")
2. **Narrative shifts**: Is the dominant narrative changing direction? Is there a new theme emerging across sources that wasn't present 3-6 months ago?
3. **Stakeholder confidence**: Do insiders, institutional commentary, and retail sentiment broadly align or diverge on the long-term outlook?
4. **Cross-source divergences**: If institutional news frames the company one way and retail sentiment frames it another, that divergence is itself a signal.
5. **Long-term catalysts and risks** identified in discourse: not earnings surprise reactions, but structural concerns about competition, regulation, or business model durability.

## What to ignore
- Single-day price reactions to earnings, macro events, or analyst upgrades/downgrades
- Short-term StockTwits/Reddit momentum chasing or "to the moon" commentary
- Any sentiment signal with a horizon shorter than 1 year

## Output
1. **Dominant narrative** for {ticker}: what is it and is it strengthening or weakening?
2. **Source-by-source breakdown** with specific evidence (cite message counts, key posts/headlines).
3. **Narrative shifts** detected: what has changed vs. the apparent prior narrative?
4. **Long-term catalysts and risks** surfaced by stakeholder discourse.
5. **Markdown table** at the end summarizing narrative themes, their direction, and evidence.

{get_language_instruction()}"""
```

Also update the section header in the data block previously labeled "News headlines — Yahoo Finance, past 7 days" to just "News headlines — Yahoo Finance":

The header is now inside `_build_system_message` so it's already updated in the rewrite above.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_long_term_config.py::test_sentiment_analyst_is_long_term -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tradingagents/agents/analysts/sentiment_analyst.py tests/test_long_term_config.py
git commit -m "feat(analysts): reframe sentiment analyst as Stakeholder & Narrative Analyst with configurable lookback"
```

---

## Task 11: New tools — get_valuation_multiples and get_quality_metrics

**Files:**
- Modify: `tradingagents/agents/utils/core_stock_tools.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_new_tools.py
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
```

- [ ] **Step 2: Run to verify tests fail**

```bash
pytest tests/test_new_tools.py -v
```

Expected: `FAILED` — `ImportError: cannot import name 'get_valuation_multiples'`

- [ ] **Step 3: Add tools to core_stock_tools.py**

Append to `tradingagents/agents/utils/core_stock_tools.py`:

```python
import yfinance as yf
import pandas as pd


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
        income = t.income_stmt
        cashflow = t.cashflow
        balance = t.balance_sheet

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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_new_tools.py -v
```

Expected: both `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tradingagents/agents/utils/core_stock_tools.py tests/test_new_tools.py
git commit -m "feat(tools): add get_valuation_multiples and get_quality_metrics tools"
```

---

## Task 12: web_tools.py — DuckDuckGo web search tool

**Files:**
- Create: `tradingagents/agents/utils/web_tools.py`

- [ ] **Step 1: Write test**

```python
# tests/test_new_tools.py — append

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
        # Reload to ensure fresh import with mock in place
        import importlib; importlib.reload(web_tools)
        result = web_tools.web_search_tool.func("cloud computing trends 2026", max_results=2)
        assert "AI boom drives cloud growth" in result
        assert "Regulatory scrutiny" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
pytest tests/test_new_tools.py::test_web_search_tool_returns_string_on_ddgs_unavailable tests/test_new_tools.py::test_web_search_tool_returns_formatted_results -v
```

Expected: `FAILED` — `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Create tradingagents/agents/utils/web_tools.py**

```python
"""Web search tool for the Macro/Secular Analyst.

Uses duckduckgo-search (no API key required). Falls back gracefully to an
empty string if the package is unavailable or the search fails.
"""

from langchain_core.tools import tool
from typing import Annotated

try:
    from duckduckgo_search import DDGS
    _DDGS_AVAILABLE = True
except ImportError:
    DDGS = None
    _DDGS_AVAILABLE = False


@tool
def web_search_tool(
    query: Annotated[str, "Search query for industry and macro research"],
    max_results: Annotated[int, "Maximum number of results to return (default 5)"] = 5,
) -> str:
    """
    Search the web for qualitative industry and macro context.
    Returns title and snippet for each result.
    Use only for qualitative narrative — do not rely on web results for financial figures.
    Falls back to empty string if search is unavailable.
    """
    if not _DDGS_AVAILABLE or DDGS is None:
        return "Web search unavailable (duckduckgo-search not installed)."
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return f"No web search results found for: {query}"
        lines = [f"## Web Search Results: {query}", ""]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body", r.get("snippet", "No snippet"))
            lines.append(f"**{i}. {title}**")
            lines.append(body)
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Web search failed for '{query}': {e}"
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_new_tools.py -v
```

Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tradingagents/agents/utils/web_tools.py tests/test_new_tools.py
git commit -m "feat(tools): add web_search_tool wrapping duckduckgo-search for macro analyst"
```

---

## Task 13: Three new analyst files

**Files:**
- Create: `tradingagents/agents/analysts/valuation_analyst.py`
- Create: `tradingagents/agents/analysts/moat_analyst.py`
- Create: `tradingagents/agents/analysts/macro_analyst.py`

- [ ] **Step 1: Write import tests**

```python
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
    from unittest.mock import MagicMock, patch
    from tradingagents.agents.analysts.valuation_analyst import create_valuation_analyst

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.tool_calls = []
    mock_result.content = "Valuation analysis: P/E is 25x vs 5yr avg 22x."
    mock_llm.bind_tools.return_value.invoke = MagicMock(return_value=mock_result)

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
    mock_llm.bind_tools.return_value.invoke = MagicMock(return_value=mock_result)

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
    mock_llm.bind_tools.return_value.invoke = MagicMock(return_value=mock_result)

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
```

- [ ] **Step 2: Run to verify tests fail**

```bash
pytest tests/test_new_analysts.py -v
```

Expected: all `FAILED` — `ModuleNotFoundError`

- [ ] **Step 3: Create valuation_analyst.py**

```python
# tradingagents/agents/analysts/valuation_analyst.py

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_language_instruction,
)
from tradingagents.agents.utils.core_stock_tools import (
    get_valuation_multiples,
)


def create_valuation_analyst(llm):
    def valuation_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_valuation_multiples,
            get_income_statement,
            get_balance_sheet,
            get_cashflow,
        ]

        system_message = (
            "You are a Valuation Analyst specializing in long-term investment analysis. "
            "Your job is to assess whether a stock is cheap, fair, or expensive relative to its own historical multiples and business quality. "
            "Use get_valuation_multiples for current P/E, P/FCF, EV/EBITDA figures. "
            "Use get_income_statement, get_balance_sheet, and get_cashflow for annual financial data to establish 5-year context. "
            "Answer: Is the current multiple justified by the business quality and growth trajectory? "
            "What is the primary valuation driver (earnings growth expectations, margin expansion, multiple re-rating)? "
            "Is the stock pricing in an optimistic or pessimistic scenario relative to its history? "
            "Conclude with a clear valuation verdict: Cheap / Fair / Expensive — and why. "
            "Append a Markdown table at the end summarizing key valuation metrics."
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "valuation_report": report,
        }

    return valuation_analyst_node
```

- [ ] **Step 4: Create moat_analyst.py**

```python
# tradingagents/agents/analysts/moat_analyst.py

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_language_instruction,
)
from tradingagents.agents.utils.core_stock_tools import get_quality_metrics


def create_moat_analyst(llm):
    def moat_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_quality_metrics,
            get_income_statement,
            get_balance_sheet,
            get_cashflow,
        ]

        system_message = (
            "You are a Moat & Quality Analyst evaluating the long-term competitive durability of a business. "
            "Use get_quality_metrics for gross margin trends, FCF conversion, and capex intensity. "
            "Use get_income_statement, get_balance_sheet, and get_cashflow for annual financial data. "
            "Answer these questions: "
            "(1) Does this business earn above its cost of capital consistently? (Look at returns on capital, not just net income.) "
            "(2) Are gross margins improving, stable, or deteriorating — and why? "
            "(3) What structural advantage sustains this business? Identify the moat type: "
            "switching costs, network effects, cost advantage, brand/intangibles, efficient scale, or none. "
            "(4) What are the primary threats to this moat over the next 3-5 years? "
            "(Technological disruption, competitive intensity, regulatory risk, margin pressure.) "
            "Conclude with a moat rating: Wide / Narrow / None — and a confidence level. "
            "Append a Markdown table summarizing quality metrics."
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "moat_report": report,
        }

    return moat_analyst_node
```

- [ ] **Step 5: Create macro_analyst.py**

```python
# tradingagents/agents/analysts/macro_analyst.py

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.web_tools import web_search_tool


def create_macro_analyst(llm):
    def macro_analyst_node(state):
        current_date = state["trade_date"]
        asset_type = state.get("asset_type", "stock")
        instrument_context = build_instrument_context(
            state["company_of_interest"], asset_type
        )

        tools = [web_search_tool]

        system_message = (
            "You are a Macro & Secular Analyst identifying 3-5 year industry tailwinds and headwinds "
            "for the company's sector. "
            "Use web_search_tool to research qualitative industry context. "
            "Focus on: "
            "(1) Secular demographic and behavioral shifts affecting the industry; "
            "(2) Regulatory trajectory — is the regulatory environment becoming more or less favorable?; "
            "(3) Technological disruption potential — is the company's core business model at risk from AI, automation, or platform shifts?; "
            "(4) Competitive intensity trends — is the industry consolidating or fragmenting?; "
            "(5) Macro sensitivity — interest rate exposure, commodity dependency, FX risk for global businesses. "
            "IMPORTANT: Do NOT cite specific financial figures (revenue, earnings, price targets) from web results. "
            "Use web results only for qualitative industry narrative. All quantitative figures must come from structured data tools. "
            "Conclude with: a ranked list of the top 3 tailwinds and top 3 headwinds for the next 3-5 years. "
            "Append a Markdown table summarizing secular trends."
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "macro_report": report,
        }

    return macro_analyst_node
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_new_analysts.py -v
```

Expected: all `PASSED`

- [ ] **Step 7: Commit**

```bash
git add tradingagents/agents/analysts/valuation_analyst.py \
        tradingagents/agents/analysts/moat_analyst.py \
        tradingagents/agents/analysts/macro_analyst.py \
        tests/test_new_analysts.py
git commit -m "feat(analysts): add valuation, moat, and macro analyst nodes"
```

---

## Task 14: Wire the three new analysts into the graph

**Files:**
- Modify: `tradingagents/agents/__init__.py`
- Modify: `tradingagents/graph/conditional_logic.py`
- Modify: `tradingagents/graph/setup.py`
- Modify: `tradingagents/graph/trading_graph.py`
- Modify: `cli/models.py`
- Modify: `cli/utils.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_new_analysts.py — append

@pytest.mark.unit
def test_new_analysts_exported_from_package():
    from tradingagents.agents import (
        create_valuation_analyst,
        create_moat_analyst,
        create_macro_analyst,
    )
    assert callable(create_valuation_analyst)
    assert callable(create_moat_analyst)
    assert callable(create_macro_analyst)


@pytest.mark.unit
def test_conditional_logic_has_new_methods():
    from tradingagents.graph.conditional_logic import ConditionalLogic
    cl = ConditionalLogic()
    assert hasattr(cl, "should_continue_valuation")
    assert hasattr(cl, "should_continue_moat")
    assert hasattr(cl, "should_continue_macro")


@pytest.mark.unit
def test_conditional_logic_valuation_routes_to_tools_when_tool_calls():
    from tradingagents.graph.conditional_logic import ConditionalLogic
    from unittest.mock import MagicMock
    cl = ConditionalLogic()
    mock_msg = MagicMock()
    mock_msg.tool_calls = [MagicMock()]
    state = {"messages": [mock_msg]}
    assert cl.should_continue_valuation(state) == "tools_valuation"


@pytest.mark.unit
def test_conditional_logic_valuation_routes_to_clear_when_no_tool_calls():
    from tradingagents.graph.conditional_logic import ConditionalLogic
    from unittest.mock import MagicMock
    cl = ConditionalLogic()
    mock_msg = MagicMock()
    mock_msg.tool_calls = []
    state = {"messages": [mock_msg]}
    assert cl.should_continue_valuation(state) == "Msg Clear Valuation"


@pytest.mark.unit
def test_new_analyst_types_in_models():
    from cli.models import AnalystType
    assert hasattr(AnalystType, "VALUATION")
    assert hasattr(AnalystType, "MOAT")
    assert hasattr(AnalystType, "MACRO")
    assert AnalystType.VALUATION.value == "valuation"
    assert AnalystType.MOAT.value == "moat"
    assert AnalystType.MACRO.value == "macro"
```

- [ ] **Step 2: Run to verify tests fail**

```bash
pytest tests/test_new_analysts.py -v
```

Expected: `FAILED`

- [ ] **Step 3: Update agents/__init__.py**

Add imports after the existing analyst imports:

```python
from .analysts.valuation_analyst import create_valuation_analyst
from .analysts.moat_analyst import create_moat_analyst
from .analysts.macro_analyst import create_macro_analyst
```

Add to `__all__`:

```python
    "create_valuation_analyst",
    "create_moat_analyst",
    "create_macro_analyst",
```

- [ ] **Step 4: Add methods to conditional_logic.py**

Append after `should_continue_fundamentals`:

```python
    def should_continue_valuation(self, state: AgentState):
        """Determine if valuation analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_valuation"
        return "Msg Clear Valuation"

    def should_continue_moat(self, state: AgentState):
        """Determine if moat analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_moat"
        return "Msg Clear Moat"

    def should_continue_macro(self, state: AgentState):
        """Determine if macro analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_macro"
        return "Msg Clear Macro"
```

- [ ] **Step 5: Update setup.py analyst_factories**

In `tradingagents/graph/setup.py`, add to the `analyst_factories` dict (after `"fundamentals"`):

```python
            "valuation": lambda: create_valuation_analyst(self.quick_thinking_llm),
            "moat": lambda: create_moat_analyst(self.quick_thinking_llm),
            "macro": lambda: create_macro_analyst(self.quick_thinking_llm),
```

Also update the docstring `selected_analysts` options list:

```python
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
                - "valuation": Valuation analyst
                - "moat": Moat/quality analyst
                - "macro": Macro/secular analyst
        """
```

- [ ] **Step 6: Add tool nodes to trading_graph.py**

In `tradingagents/graph/trading_graph.py`, add imports at the top (after existing agent_utils imports):

```python
from tradingagents.agents.utils.core_stock_tools import (
    get_valuation_multiples,
    get_quality_metrics,
)
from tradingagents.agents.utils.web_tools import web_search_tool
```

In `_create_tool_nodes()`, add three new entries after `"fundamentals"`:

```python
            "valuation": ToolNode(
                [
                    get_valuation_multiples,
                    get_income_statement,
                    get_balance_sheet,
                    get_cashflow,
                ]
            ),
            "moat": ToolNode(
                [
                    get_quality_metrics,
                    get_income_statement,
                    get_balance_sheet,
                    get_cashflow,
                ]
            ),
            "macro": ToolNode(
                [
                    web_search_tool,
                ]
            ),
```

Also update the default `selected_analysts` in `TradingAgentsGraph.__init__` signature (line 55):

```python
        selected_analysts=["market", "social", "news", "fundamentals", "valuation", "moat", "macro"],
```

- [ ] **Step 7: Update cli/models.py**

Add three new values to `AnalystType`:

```python
class AnalystType(str, Enum):
    MARKET = "market"
    SOCIAL = "social"
    NEWS = "news"
    FUNDAMENTALS = "fundamentals"
    VALUATION = "valuation"
    MOAT = "moat"
    MACRO = "macro"
```

- [ ] **Step 8: Update cli/utils.py ANALYST_ORDER**

Add after the existing entries in `ANALYST_ORDER`:

```python
ANALYST_ORDER = [
    ("Market Analyst", AnalystType.MARKET),
    ("Sentiment Analyst", AnalystType.SOCIAL),
    ("News Analyst", AnalystType.NEWS),
    ("Fundamentals Analyst", AnalystType.FUNDAMENTALS),
    ("Valuation Analyst", AnalystType.VALUATION),
    ("Moat & Quality Analyst", AnalystType.MOAT),
    ("Macro & Secular Analyst", AnalystType.MACRO),
]
```

- [ ] **Step 9: Run tests**

```bash
pytest tests/test_new_analysts.py -v
```

Expected: all `PASSED`

- [ ] **Step 10: Run full unit suite**

```bash
pytest -m unit
```

Expected: all `PASSED`

- [ ] **Step 11: Commit**

```bash
git add tradingagents/agents/__init__.py \
        tradingagents/graph/conditional_logic.py \
        tradingagents/graph/setup.py \
        tradingagents/graph/trading_graph.py \
        cli/models.py \
        cli/utils.py \
        tests/test_new_analysts.py
git commit -m "feat(graph): wire valuation, moat, macro analysts into graph, conditional logic, and CLI"
```

---

## Task 15: Researcher and debate agents — investment horizon context

**Files:**
- Modify: `tradingagents/agents/researchers/bull_researcher.py`
- Modify: `tradingagents/agents/researchers/bear_researcher.py`
- Modify: `tradingagents/agents/risk_mgmt/aggressive_debator.py`
- Modify: `tradingagents/agents/risk_mgmt/conservative_debator.py`
- Modify: `tradingagents/agents/risk_mgmt/neutral_debator.py`
- Modify: `tradingagents/agents/managers/portfolio_manager.py`

- [ ] **Step 1: Write test**

```python
# tests/test_long_term_config.py — append

@pytest.mark.unit
def test_researcher_prompts_include_new_reports():
    import inspect
    import tradingagents.agents.researchers.bull_researcher as b
    src = inspect.getsource(b)
    assert "valuation_report" in src
    assert "moat_report" in src
    assert "macro_report" in src
    assert "investment_horizon" in src


@pytest.mark.unit
def test_debate_agent_prompts_include_horizon():
    import inspect
    import tradingagents.agents.risk_mgmt.aggressive_debator as a
    import tradingagents.agents.risk_mgmt.conservative_debator as c
    import tradingagents.agents.risk_mgmt.neutral_debator as n
    import tradingagents.agents.managers.portfolio_manager as pm
    for mod in [a, c, n, pm]:
        src = inspect.getsource(mod)
        assert "investment_horizon" in src or "3-5 year" in src, \
            f"{mod.__name__} missing investment horizon context"
```

- [ ] **Step 2: Run to verify tests fail**

```bash
pytest tests/test_long_term_config.py::test_researcher_prompts_include_new_reports tests/test_long_term_config.py::test_debate_agent_prompts_include_horizon -v
```

Expected: `FAILED`

- [ ] **Step 3: Update bull_researcher.py**

In `bull_node`, add new report reads after `fundamentals_report`:

```python
        valuation_report = state.get("valuation_report", "")
        moat_report = state.get("moat_report", "")
        macro_report = state.get("macro_report", "")
        investment_horizon = state.get("investment_horizon", "3-5 years")
```

Add to the prompt string (after the existing `{fundamentals_label}: {fundamentals_report}` line):

```python
Valuation report: {valuation_report}
Moat & quality report: {moat_report}
Macro & secular report: {macro_report}

Investment horizon context: The investment horizon is {investment_horizon}. Weight your bull arguments for this timeframe. Short-term price volatility is NOT a risk at this horizon — focus on structural business quality and long-term growth catalysts.
```

- [ ] **Step 4: Update bear_researcher.py**

Read the file and apply the same pattern as bull_researcher:
- Add reads for `valuation_report`, `moat_report`, `macro_report`, `investment_horizon`
- Inject into prompt:

```python
Valuation report: {valuation_report}
Moat & quality report: {moat_report}
Macro & secular report: {macro_report}

Investment horizon context: The investment horizon is {investment_horizon}. Weight your bear arguments for structural risks that could materially harm the business over this timeframe. Short-term price weakness is not a bear thesis at this horizon — focus on business model deterioration, competitive displacement, or valuation excess.
```

- [ ] **Step 5: Update aggressive_debator.py**

Add reads at the top of `aggressive_node`:

```python
        investment_horizon = state.get("investment_horizon", "3-5 years")
```

Add to the prompt string, after the existing fundamentals block:

```python
Investment horizon: {investment_horizon}. Short-term price volatility is not a risk at this horizon. Focus your aggressive case on structural growth opportunities and why cautious arguments underweight the long-term upside.
```

- [ ] **Step 6: Update conservative_debator.py**

Read the file. Apply the same pattern as aggressive_debator:
- Add `investment_horizon = state.get("investment_horizon", "3-5 years")`
- Add to prompt: `"Investment horizon: {investment_horizon}. At this timeframe, short-term volatility is noise. Focus your conservative case on structural risks: competitive moat erosion, regulatory headwinds, valuation vs. long-term growth potential."`

- [ ] **Step 7: Update neutral_debator.py**

Apply same pattern:
- Add `investment_horizon = state.get("investment_horizon", "3-5 years")`
- Add to prompt: `"Investment horizon: {investment_horizon}. Weigh both structural upside and structural risks. Short-term price movements should not influence your balanced assessment."`

- [ ] **Step 8: Update portfolio_manager.py**

Add to the prompt in `portfolio_manager_node`, in the `**Context:**` section:

```python
        investment_horizon = state.get("investment_horizon", "3-5 years")
```

In the prompt f-string, add after `{lessons_line}`:

```python
- Investment horizon: **{investment_horizon}**. The final decision should reflect this multi-year holding period. Short-term price volatility is not a relevant risk factor at this horizon.
```

- [ ] **Step 9: Also update trader.py system prompt**

In `tradingagents/agents/trader/trader.py`, update the system message:

```python
            "content": (
                "You are an investment analyst translating a research team's investment plan "
                "into a concrete investment decision for a long-term (3-5 year) horizon. "
                "Based on your analysis, provide a specific recommendation to buy, sell, or hold. "
                "Anchor your reasoning in the analysts' reports and the research plan. "
                "Your conviction score must reflect the quality and clarity of the long-term thesis, "
                "not short-term price predictions."
                + get_language_instruction()
            ),
```

Update the user message content:

```python
                "content": (
                    f"Based on a comprehensive analysis by a team of analysts, here is an investment "
                    f"plan tailored for {company_name}. {instrument_context} This plan incorporates "
                    f"insights from technical positioning, fundamental quality, valuation, competitive moat, "
                    f"macro/secular trends, stakeholder narrative, and news analysis. Use this plan as "
                    f"a foundation for evaluating the long-term investment decision.\n\n"
                    f"Proposed Investment Plan: {investment_plan}\n\n"
                    f"Provide your investment decision with conviction score, thesis horizon, and key catalysts."
                ),
```

- [ ] **Step 10: Run tests**

```bash
pytest tests/test_long_term_config.py -v
```

Expected: all `PASSED`

- [ ] **Step 11: Run full unit suite**

```bash
pytest -m unit
```

Expected: all `PASSED`

- [ ] **Step 12: Commit**

```bash
git add tradingagents/agents/researchers/bull_researcher.py \
        tradingagents/agents/researchers/bear_researcher.py \
        tradingagents/agents/risk_mgmt/aggressive_debator.py \
        tradingagents/agents/risk_mgmt/conservative_debator.py \
        tradingagents/agents/risk_mgmt/neutral_debator.py \
        tradingagents/agents/managers/portfolio_manager.py \
        tradingagents/agents/trader/trader.py \
        tests/test_long_term_config.py
git commit -m "feat(agents): inject investment horizon and new report fields into all debate and decision agents"
```

---

## Task 16: CLI wizard — add investment horizon step

**Files:**
- Modify: `cli/utils.py`
- Modify: `cli/main.py`

- [ ] **Step 1: Write test**

```python
# tests/test_long_term_config.py — append

@pytest.mark.unit
def test_ask_investment_horizon_importable():
    from cli.utils import ask_investment_horizon
    assert callable(ask_investment_horizon)
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_long_term_config.py::test_ask_investment_horizon_importable -v
```

Expected: `FAILED` — `ImportError`

- [ ] **Step 3: Add ask_investment_horizon to cli/utils.py**

Append to `tradingagents/cli/utils.py` (after `ask_output_language`):

```python
def ask_investment_horizon() -> str:
    """Ask for investment horizon."""
    choice = questionary.select(
        "Select Investment Horizon:",
        choices=[
            questionary.Choice("1-3 years (medium term)", "1-3 years"),
            questionary.Choice("3-5 years (long term — default)", "3-5 years"),
            questionary.Choice("5-10 years (very long term)", "5-10 years"),
        ],
        default="3-5 years",
        style=questionary.Style([
            ("selected", "fg:yellow noinherit"),
            ("highlighted", "fg:yellow noinherit"),
            ("pointer", "fg:yellow noinherit"),
        ]),
    ).ask()

    if not choice:
        return "3-5 years"
    return choice
```

- [ ] **Step 4: Add wizard step in cli/main.py**

In `get_user_selections()`, add a new Step 3 block between the current "Step 2: Analysis Date" block and the current "Step 3: Output Language" block. Renumber the existing steps 3+ to 4+.

After line 527 (`analysis_date = get_analysis_date()`), add:

```python
    # Step 3: Investment Horizon
    console.print(
        create_question_box(
            "Step 3: Investment Horizon",
            "Select the investment horizon for this analysis"
        )
    )
    investment_horizon = ask_investment_horizon()
```

Update the existing step labels:
- "Step 3: Output Language" → "Step 4: Output Language"  
- "Step 4: Analysts Team" → "Step 5: Analysts Team"
- "Step 5: Research Depth" → "Step 6: Research Depth"
- "Step 6: LLM Provider" → "Step 7: LLM Provider"
- "Step 7: Thinking Agents" → "Step 8: Thinking Agents"
- "Step 8: Thinking Mode/Reasoning Effort/Effort Level" → "Step 9: ..."

Add `"investment_horizon": investment_horizon` to the return dict in `get_user_selections()`.

- [ ] **Step 5: Wire investment_horizon into config in run_analysis()**

In `run_analysis()`, after line `config["output_language"] = selections.get("output_language", "English")`, add:

```python
    config["investment_horizon"] = selections.get("investment_horizon", "3-5 years")
```

- [ ] **Step 6: Export ask_investment_horizon from utils**

In `cli/utils.py`, the function is already added; verify it's accessible via `from cli.utils import ask_investment_horizon`.

In `cli/main.py`, add to the `from cli.utils import *` (already uses star import, so it's automatic if added to utils.py).

- [ ] **Step 7: Run tests**

```bash
pytest tests/test_long_term_config.py -v
```

Expected: all `PASSED`

- [ ] **Step 8: Run full test suite**

```bash
pytest tests/
```

Expected: all `PASSED`

- [ ] **Step 9: Commit**

```bash
git add cli/utils.py cli/main.py tests/test_long_term_config.py
git commit -m "feat(cli): add investment horizon wizard step (Step 3)"
```

---

## Task 17: Final verification

- [ ] **Step 1: Run all unit tests**

```bash
pytest -m unit -v
```

Expected: all `PASSED`

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/
```

Expected: all `PASSED`. Any `FAILED` must be fixed before proceeding.

- [ ] **Step 3: Verify import chain for new analysts**

```bash
python -c "
from tradingagents.agents import create_valuation_analyst, create_moat_analyst, create_macro_analyst
from tradingagents.agents.utils.web_tools import web_search_tool
from tradingagents.agents.utils.core_stock_tools import get_valuation_multiples, get_quality_metrics
from tradingagents.agents.schemas import InvestmentProposal, render_trader_proposal
from cli.models import AnalystType
print('All imports OK')
print('Analyst types:', [a.value for a in AnalystType])
"
```

Expected output:
```
All imports OK
Analyst types: ['market', 'social', 'news', 'fundamentals', 'valuation', 'moat', 'macro']
```

- [ ] **Step 4: Verify config**

```bash
python -c "
from tradingagents.default_config import DEFAULT_CONFIG
required_keys = ['investment_horizon', 'news_lookback_days', 'sentiment_lookback_days',
                 'look_back_days', 'financial_statement_frequency', 'outcome_tracking_enabled',
                 'holding_days']
for k in required_keys:
    print(f'{k}: {DEFAULT_CONFIG[k]}')
assert DEFAULT_CONFIG['global_news_lookback_days'] == 180, 'global_news_lookback_days not updated'
print('All config keys OK')
"
```

Expected: all values print without error.

- [ ] **Step 5: Commit final tag**

```bash
git add -p  # stage any unstaged changes
git commit -m "chore: long-term investment system — all phases complete"
```

---

## Verification checklist

After all tasks are complete, run these manual checks:

```bash
# Run a test analysis to see all 7 analysts
python main.py  # or: tradingagents CLI → select AAPL

# Confirm:
# 1. All 7 analysts appear (4 reframed + valuation + moat + macro)
# 2. No "past week" or "for traders" language in any analyst report
# 3. InvestmentProposal has conviction_score, thesis_horizon, key_catalysts
# 4. PortfolioDecision.time_horizon is populated (e.g. "3-5 years")
# 5. No reflection/grading error (outcome_tracking_enabled=False)
# 6. Macro analyst web search returns results (not "unavailable")
# 7. CLI shows Step 3: Investment Horizon before analyst selection
```
