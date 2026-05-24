# Long-Horizon Investing Plugin

A Claude Code plugin for medium-to-long-term equity research (3/5/10-year horizons). Analyzes a single ticker using a 4-stage parallel subagent pipeline and produces an **Initiate / Add / Hold / Trim / Avoid** verdict backed by kill-criteria.

**This is a research opinion tool. It never executes trades, connects to a broker, or manages a portfolio.**

## Install

```bash
# Install the plugin in Claude Code
claude plugin install path/to/long-horizon-investing/

# Set your FRED API key (free at https://fred.stlouisfed.org/docs/api/api_key.html)
export FRED_API_KEY=your_key_here
```

MCP servers (`edgar-mcp`, `yfinance-mcp`, `fred-mcp`) are declared in `.mcp.json` and installed automatically via `uvx`.

## Usage

```
/analyze COST                          # Full 10-year US analysis
/analyze COST --horizon 5              # 5-year horizon
/analyze ASML --accept-eu-degraded     # EU ticker (degraded mode, no EDGAR)
/revisit COST                          # Check kill-criteria against current data
/debate-only COST                      # Re-run debate from cached analyst files
```

## Output

Results are written to `research/{TICKER}/` (gitignored):
- `fundamentals.json`, `moat.json`, `valuation.json`, `macro.json`, `insider.json` — analyst envelopes
- `bull.json`, `bear.json` — researcher arguments
- `risk_aggressive.json`, `risk_conservative.json`, `risk_neutral.json` — risk debate
- `verdict.json` — structured verdict with kill-criteria
- `report.md` — human-readable research note
- `history.md` — append-only run log

See `samples/COST/` for a worked example.

## Architecture

```
/analyze TICKER
  Stage 1 (parallel): 5 analyst subagents → research/{T}/*.json
  Stage 2 (parallel): bull + bear researchers → bull.json, bear.json
  Stage 3 (parallel): 3 risk debators → risk_*.json
  Stage 4 (sequential): synthesizer → verdict.json + report.md
```

## Data sources

| Source | What for | Auth |
|---|---|---|
| EdgarTools MCP | US filings, Form 4, 13F, DEF 14A | None (US only) |
| yfinance MCP | Price, dividends, buybacks, basic financials | None |
| FRED MCP | Macro: rates, inflation, GDP | Free API key |
| Web search | Secular trends, moat qualitative | Via Claude |

**EU mode:** For non-US tickers, EDGAR data is unavailable. Fundamentals fall back to yfinance-only. Insider/13F data is absent. Initiate/Add verdicts are blocked unless `--accept-eu-degraded` is passed.

## Attribution

Built on:
- [financial-services](https://github.com/anthropics/financial-services) (Apache-2.0, Anthropic) — skill patterns for DCF and comps
- [InvestAgents](https://github.com/bolah/InvestAgents) (Apache-2.0, Bence Olah) — bull/bear debate and risk debate agent prompts

See `NOTICE` for full attribution.
