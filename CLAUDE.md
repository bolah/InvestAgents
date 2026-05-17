# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install
uv sync                  # preferred
pip install .            # alternative

# Run
tradingagents            # installed CLI entry point
python main.py           # minimal programmatic example

# Tests
pytest                                                          # all tests
pytest -m unit                                                  # fast isolated tests only
pytest -m integration                                           # tests requiring external services
pytest tests/test_signal_processing.py                          # single file
pytest tests/test_memory_log.py::TestClass::test_method         # single test

# Docker
cp .env.example .env
docker compose run --rm tradingagents
docker compose --profile ollama run --rm tradingagents-ollama   # local LLM
```

No linter or formatter is configured in this project.

## Architecture

The system is a **LangGraph state machine** that runs 11+ LLM agents in a directed graph. The main entry point is `TradingAgentsGraph.propagate(ticker, date)` in `tradingagents/graph/trading_graph.py`, which returns `(final_state, decision_signal)`.

### Package Map

| Package | Role |
|---|---|
| `tradingagents/graph/` | LangGraph wiring, state machine, checkpointing, memory log, signal extraction |
| `tradingagents/agents/` | All LLM agent definitions, shared state TypedDicts, Pydantic schemas for structured outputs |
| `tradingagents/dataflows/` | Data vendor abstraction — routes tool calls to yfinance or Alpha Vantage with auto-fallback |
| `tradingagents/llm_clients/` | Provider-agnostic LLM factory (OpenAI, Anthropic, Google, xAI, DeepSeek, Qwen, GLM, OpenRouter, Ollama, Azure) |
| `cli/` | Rich TUI — interactive wizard, live streaming display, report saving |

### Agent Pipeline

```
START
  └─► Analyst Team (configurable subset, sequential)
        ├─ Market Analyst       ─┐ each loops: tool_calls? → tools node : clear messages
        ├─ Social Media Analyst  │
        ├─ News Analyst          │
        └─ Fundamentals Analyst ─┘
  └─► Research Team (cyclic debate, up to max_debate_rounds)
        ├─ Bull Researcher ◄─► Bear Researcher
        └─ Research Manager (judge → structured ResearchPlan)
  └─► Trader (structured InvestmentProposal: Buy/Hold/Sell + conviction_score/thesis_horizon/key_catalysts)
  └─► Risk Management (cyclic 3-way debate, up to max_risk_discuss_rounds)
        ├─ Aggressive ◄─► Conservative ◄─► Neutral
        └─ Portfolio Manager (judge → structured PortfolioDecision: 5-tier rating)
  └─► END
```

Two LLMs are used: `quick_thinking_llm` for analysts/researchers/trader/risk debaters; `deep_thinking_llm` for the two judge agents (Research Manager, Portfolio Manager).

### State Object

`AgentState` (in `agents/utils/agent_states.py`) flows through the entire graph. Key fields:
- `company_of_interest`, `trade_date`
- `market_report`, `sentiment_report`, `news_report`, `fundamentals_report` — strings filled by each analyst
- `investment_debate_state: InvestDebateState` — bull/bear histories + judge decision
- `valuation_report`, `moat_report`, `macro_report` — strings filled by the three new long-term analysts
- `trader_investment_plan` — InvestmentProposal rendered to markdown
- `risk_debate_state: RiskDebateState` — 3-way risk debate + judge decision
- `final_trade_decision` — PortfolioDecision rendered to markdown
- `past_context` — injected memory log (same-ticker history + cross-ticker lessons)

### Structured Output

Three agents use Pydantic schemas with provider-native structured output (`agents/schemas.py`):
- `ResearchManager` → `ResearchPlan`
- `Trader` → `InvestmentProposal`
- `PortfolioManager` → `PortfolioDecision`

Each schema has a `render_*` function that converts the parsed object back to markdown for storage and downstream agents.

### Data Flow

Agents call abstract tool functions in `agents/utils/agent_utils.py` → `agents/utils/core_stock_tools.py` et al. → `dataflows/interface.py:route_to_vendor()` → `dataflows/y_finance.py` or `dataflows/alpha_vantage*.py`. Alpha Vantage rate-limit hits fall back to yfinance automatically.

### LLM Client Factory

`llm_clients/factory.py:create_llm_client(provider, model, base_url, **kwargs)` dispatches lazily to one of four clients. All OpenAI-compatible providers (xAI, DeepSeek, Qwen, GLM, Ollama, OpenRouter) are routed through `OpenAIClient`. All clients expose `.get_llm()` returning a LangChain chat model.

### Persistence

- **Decision log**: `~/.tradingagents/memory/trading_memory.md` — append-only. On next same-ticker run, past performance vs SPY is fetched and reflected on, then injected as `past_context` into the Portfolio Manager prompt.
- **Checkpoints**: per-ticker SQLite at `~/.tradingagents/cache/checkpoints/<TICKER>.db` via `langgraph-checkpoint-sqlite`. Opt-in via `config["checkpoint_enabled"] = True` or `--checkpoint` CLI flag.
- **Results**: JSON state log at `~/.tradingagents/logs/<TICKER>/TradingAgentsStrategy_logs/full_states_log_<date>.json`.

### Configuration

All runtime defaults live in `tradingagents/default_config.py`. Key config keys: `llm_provider`, `backend_url`, `deep_think_llm`, `quick_think_llm`, `max_debate_rounds`, `max_risk_discuss_rounds`, `online_tools` (bool), `selected_analysts` (list).
