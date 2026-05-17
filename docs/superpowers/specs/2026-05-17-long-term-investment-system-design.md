# Long-Term Investment System — Design Spec

**Date:** 2026-05-17
**Horizon target:** 3-5 years (emphasis on 5yr+)
**Approach:** Surgical in-place rewrite — keep LangGraph graph structure, replace prompts/schemas/data for long-term investing

---

## Context

InvestAgents is currently a short-term trading system. Every component is tuned for single-trade, near-term decisions:
- News and sentiment lookbacks are hardcoded at 7 days
- Outcome tracking grades decisions on 5-day (1 trading week) returns
- All four analyst prompts frame their output for "traders" making "this week" decisions
- The `TraderProposal` schema has `stop_loss` and `entry_price` fields — day-trading concepts
- The `PortfolioDecision.time_horizon` field is Optional and defaults to a "3-6 months" example

The goal is to shift to a 3-5 year investment horizon: value/quality investing, thesis-driven conviction, and structural business analysis. The LangGraph pipeline and agent topology are preserved; only prompts, schemas, data windows, and analyst composition change.

---

## What Is NOT Changing

- LangGraph graph topology (no node rewiring beyond adding new analysts)
- Agent pipeline order: Analysts → Research Debate → Trader → Risk Debate → Portfolio Manager
- All provider/LLM factory code (`llm_clients/`)
- Checkpoint/persistence infrastructure
- CLI command structure (only adds one wizard step)
- Dataflows vendor abstraction (`dataflows/interface.py`, `route_to_vendor()`)
- Alpha Vantage / yfinance client code (except new tool functions added)

---

## Phase 1 — Configuration Layer

**File:** `tradingagents/default_config.py`

Add keys:
```python
"investment_horizon": "3-5 years",         # injected into all agent prompts
"news_lookback_days": 180,                  # was hardcoded at 7
"sentiment_lookback_days": 90,              # was hardcoded at 7
"look_back_days": 365,                      # was hardcoded at 30 in tools
"financial_statement_frequency": "annual",  # was "quarterly"
"outcome_tracking_enabled": False,          # disables deferred reflection grading
"holding_days": 252,                        # stub for future use (was hardcoded at 5)
```

Update existing:
```python
"global_news_lookback_days": 180,           # was 7
```

**File:** `tradingagents/agents/utils/agent_states.py`

Add to `AgentState`:
```python
investment_horizon: str    # e.g. "3-5 years"
valuation_report: str      # new Valuation Analyst output
moat_report: str           # new Moat/Quality Analyst output
macro_report: str          # new Macro/Secular Analyst output
```

**File:** `tradingagents/graph/trading_graph.py`

- Guard `_resolve_pending_entries()` call with `config.get("outcome_tracking_enabled", False)`
- Add `investment_horizon` to the initial state populated in `propagate()`

---

## Phase 2 — Schema Changes

**File:** `tradingagents/agents/schemas.py`

### `TraderProposal` → `InvestmentProposal`

Remove: `entry_price`, `stop_loss`

Add:
```python
conviction_score: int = Field(
    description="Conviction level 1-10. 7+ = meaningful position. Below 5 = insufficient clarity to invest."
)
thesis_horizon: str = Field(
    description="Expected timeframe for thesis to play out, e.g. '3-5 years'."
)
key_catalysts: str = Field(
    description="2-3 concrete milestones or events that would validate or invalidate the thesis."
)
```

Keep: `action` (BUY/HOLD/SELL), `reasoning`, `position_sizing`

Update `render_trader_proposal()` to render the new fields.

### `PortfolioDecision`

- `time_horizon`: `Optional[str]` → `str` (required); update example from `"3-6 months"` to `"3-5 years"`
- `executive_summary` docstring: replace "entry strategy, position sizing, key risk levels" with "investment thesis, conviction level, expected catalysts, and holding horizon"

### `ResearchPlan`

- `strategic_actions` docstring: replace "Concrete steps for the **trader**" with "Concrete steps for the **investor**"

### Import sites to update

- `tradingagents/agents/trader/trader.py` — `TraderProposal` → `InvestmentProposal`
- `tradingagents/graph/trading_graph.py` — `trader_investment_plan` state manipulation
- `tradingagents/graph/signal_processing.py` — schema parsing

---

## Phase 3 — Existing Analyst Rewrites (4 files)

### `tradingagents/agents/analysts/market_analyst.py` → "Technical Signal Analyst"

- Purpose reframed: identify whether price level is a reasonable entry for a 3-5 year position, or a structural downtrend ("falling knife" risk)
- Lookback emphasis: 52-week range, 200-SMA, long-term relative strength
- RSI/MACD kept as secondary signals with explicit prompt note: "These indicators carry low weight for multi-year decisions. Only flag if they indicate a severe downtrend."
- Output framing: "Is the current technical picture consistent with initiating a long-term position?"

### `tradingagents/agents/analysts/fundamentals_analyst.py`

- Remove "over the past week" → replace with "over the investment horizon"
- Remove "to inform traders" → "to inform long-term investors"
- Prompt asks for: revenue CAGR (5yr), gross margin trend, operating leverage, capital allocation quality (buybacks vs. dilution, FCF reinvestment), balance sheet durability (net debt/EBITDA)
- Financial statement fetches use `financial_statement_frequency` config key (annual)

### `tradingagents/agents/analysts/news_analyst.py`

- Replace 7-day lookback with `config["news_lookback_days"]` (180 days)
- Prompt reframed: structural trends over 3-5 years — regulatory shifts, competitive disruptions, macro tailwinds, management changes. NOT earnings surprises or day-to-day price moves.

### `tradingagents/agents/analysts/sentiment_analyst.py` → "Stakeholder & Narrative Analyst"

- Remove `_seven_days_back()` hardcoding; use `config["sentiment_lookback_days"]` (90 days)
- Prompt reframed: "What is the enduring narrative the market has about this company? Is it shifting?"
- Explicitly states: "Short-term sentiment fluctuations are noise. Focus only on durable narrative changes that could affect 3-5 year positioning."

---

## Phase 4 — Three New Analyst Files

All three follow the existing pattern: `@tool`-decorated functions, LangGraph node, looping tool-call structure, report written to state.

### `tradingagents/agents/analysts/valuation_analyst.py` → `state["valuation_report"]`

**Tools:** Existing `get_income_statement`, `get_balance_sheet`, `get_cashflow` (annual) + new `get_valuation_multiples()` in `core_stock_tools.py`

`get_valuation_multiples(ticker, curr_date)`: derives P/E, P/FCF, EV/EBITDA from yfinance; returns current figures alongside 5-year historical averages.

**Prompt:** "Is this stock cheap, fair, or expensive relative to its own 5-year multiple history? Identify the primary valuation driver and whether the current multiple is justified by business quality and growth."

### `tradingagents/agents/analysts/moat_analyst.py` → `state["moat_report"]`

**Tools:** Existing financial statement tools (annual) + new `get_quality_metrics()` in `core_stock_tools.py`

`get_quality_metrics(ticker, curr_date)`: derives ROIC (NOPAT / invested capital), gross margin trend (5yr), operating leverage, FCF conversion (FCF / net income), capex intensity from annual statements.

**Prompt:** "Does this business earn above its cost of capital consistently? Are margins improving or deteriorating? What structural advantage (switching costs, network effects, cost advantage, brand) sustains or threatens this?"

### `tradingagents/agents/analysts/macro_analyst.py` → `state["macro_report"]`

**Tools:** New `web_search_tool()` in new file `tradingagents/agents/utils/web_tools.py`

`web_search_tool(query, max_results=5)`: wraps `duckduckgo-search` package (no API key). Returns title + snippet per result. Fails gracefully to empty string.

**Prompt:** "Identify the 3-5 year industry tailwinds and headwinds for this company's sector. Focus on secular demographic shifts, regulatory trajectory, technological disruption potential, and competitive intensity trends. **Do not cite specific financial figures from web results — use only for qualitative industry narrative.**"

**Graph wiring:** All three added to `selected_analysts` default list in `default_config.py`. No graph topology change needed.

---

## Phase 5 — Research/Trader/Risk Debate Prompt Updates

**Files:** `bull_researcher.py`, `bear_researcher.py`, `aggressive_debator.py`, `conservative_debator.py`, `neutral_debator.py`, `trader.py`, `portfolio_manager.py`

Add to each system prompt:
> "The investment horizon is {investment_horizon}. Weight your arguments for this timeframe. Short-term price volatility is not a risk at this horizon — focus on structural and fundamental risks."

Trader system prompt: "trading agent" → "investment analyst"; "trading decision" → "investment decision".

---

## Phase 6 — CLI Wizard

**File:** `cli/main.py`

Add one step in `get_user_selections()` between the date step and analyst selection:

```
Step N: Investment Horizon
  Options: "1-3 years", "3-5 years" (default), "5-10 years", "Custom (enter months)"
```

Result stored as `config["investment_horizon"]`, propagated into state in `propagate()`.

---

## Phase 7 — Memory Reflection Stub

**File:** `tradingagents/graph/trading_graph.py`

Wrap `_resolve_pending_entries()` body with:
```python
if not self.config.get("outcome_tracking_enabled", False):
    return
```

Memory log still writes decisions (`store_decision()` unchanged). Grading and reflection generation are skipped until Phase 9.

Add `"holding_days": 252` to `DEFAULT_CONFIG`.

---

## Critical Files (in execution order)

1. `tradingagents/default_config.py`
2. `tradingagents/agents/utils/agent_states.py`
3. `tradingagents/graph/trading_graph.py`
4. `tradingagents/agents/schemas.py`
5. `tradingagents/agents/trader/trader.py`
6. `tradingagents/graph/signal_processing.py`
7. `tradingagents/agents/analysts/market_analyst.py`
8. `tradingagents/agents/analysts/fundamentals_analyst.py`
9. `tradingagents/agents/analysts/news_analyst.py`
10. `tradingagents/agents/analysts/sentiment_analyst.py`
11. `tradingagents/agents/utils/core_stock_tools.py`
12. `tradingagents/agents/utils/web_tools.py` *(new)*
13. `tradingagents/agents/analysts/valuation_analyst.py` *(new)*
14. `tradingagents/agents/analysts/moat_analyst.py` *(new)*
15. `tradingagents/agents/analysts/macro_analyst.py` *(new)*
16. `tradingagents/agents/analysts/bull_researcher.py`, `bear_researcher.py`, `aggressive_debator.py`, `conservative_debator.py`, `neutral_debator.py`
17. `cli/main.py`

---

## New Dependencies

- `duckduckgo-search` — add to `pyproject.toml`; used only in `web_tools.py`

---

## Verification

```bash
# Full run on a known ticker
python main.py  # or: tradingagents CLI → select AAPL or MSFT

# Confirm:
# 1. All 7 analysts appear in output (4 reframed + 3 new)
# 2. No "past week" or "traders" language in any analyst report
# 3. InvestmentProposal contains conviction_score, thesis_horizon, key_catalysts
# 4. PortfolioDecision.time_horizon is populated (e.g. "3-5 years")
# 5. No reflection/grading error (outcome_tracking_enabled=False)
# 6. Macro analyst web search returns results

pytest -m unit          # fast unit tests
pytest tests/           # full suite — catches any import rename breakage
```

---

## Future Phases (out of scope)

- **Phase 8:** Replace yfinance with SEC EDGAR for financial statements
- **Phase 9:** Re-enable outcome tracking with `holding_days=252` (annual returns vs. benchmark)
- **Phase 10:** Configurable horizon parameter with prompt scaling (1-3y vs 5-10y analyst personas)
