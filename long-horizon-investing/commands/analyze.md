---
description: Run a full long-horizon equity analysis for a ticker (5 analysts → bull/bear → 3-way risk debate → synthesis + verdict).
argument-hint: "[TICKER] [--horizon 3|5|10] [--accept-eu-degraded]"
---

# /analyze [TICKER]

Run a full long-horizon research pipeline for the given ticker.

**Usage:**
- `/analyze COST` — full US run, 10-year horizon (default)
- `/analyze COST --horizon 5` — 5-year horizon
- `/analyze ASML --accept-eu-degraded` — EU ticker, acknowledges degraded mode

## Steps

1. Parse the ticker and options. If no ticker provided, ask for one.

2. Create the output directory: `research/{TICKER}/`

3. **Stage 1 — Analysts (run in parallel):**
   Dispatch all 5 analyst subagents simultaneously using the Agent tool:
   - `fundamentals` agent with `$TICKER` and horizon
   - `moat` agent with `$TICKER` and horizon
   - `valuation` agent with `$TICKER` and horizon
   - `macro-secular` agent with `$TICKER` and horizon
   - `insider-ownership` agent with `$TICKER` and horizon

   Wait for all 5 to complete before Stage 2.

4. **Stage 2 — Researchers (run in parallel):**
   Dispatch both researcher subagents simultaneously:
   - `bull-researcher` agent
   - `bear-researcher` agent

   Wait for both to complete before Stage 3.

5. **Stage 3 — Risk debate (run in parallel):**
   Dispatch all 3 risk debators simultaneously:
   - `aggressive-debator` agent
   - `conservative-debator` agent
   - `neutral-debator` agent

   Wait for all 3 to complete before Stage 4.

6. **Stage 4 — Synthesis (sequential):**
   Run `synthesizer` agent. It reads all 10 prior files and writes `verdict.json` and `report.md`.

7. **Display the verdict:**
   Read `research/{TICKER}/verdict.json` and `research/{TICKER}/report.md` and display the full report.

## EU degraded mode

If `--accept-eu-degraded` is NOT passed and the ticker is EU (insider.json shows `eu_mode_degraded: true`), halt after Stage 1 and display:

```
⚠️  EU mode: EDGAR data unavailable for {TICKER}.
    Insider/13F data is absent. Fundamentals are yfinance-only.
    An Initiate or Add verdict is blocked in EU mode without explicit consent.
    
    To proceed: /analyze {TICKER} --accept-eu-degraded
    This acknowledges that the verdict is based on incomplete data.
```
