# Design: `/scan-region` Pipeline

**Date:** 2026-07-01
**Status:** Approved

## Goal

A fully automated pipeline that takes a country or region name, determines whether the country or a specific sector within it has a genuine investment edge, and outputs a structured brief recommending the relevant country or sector ETF — or a clear "pass" if nothing clears the bar.

The target instrument is always an ETF (country or sector-within-country), never individual stocks. Individual stocks are evidence, not output.

---

## Command

```
/scan-region "South Korea"
/scan-region "Brazil"
/scan-region "Southeast Asia"
```

The pipeline resolves the region name to the primary liquid country ETF using yfinance and web search, then uses that ETF's top holdings as the investable universe.

- Single country → most-liquid country ETF (e.g. EWY for South Korea, EWZ for Brazil)
- Multi-country region → most-liquid broad regional ETF (e.g. ASEA for Southeast Asia, VGK for Europe). The scout picks one ETF; if none is clearly dominant it flags this and halts with a suggestion to narrow the region.

Output directory: `research/{REGION_SLUG}/` (e.g. `research/south_korea/`)

---

## Pipeline Stages

### Stage 1 — Parallel bootstrap

Two agents fire simultaneously:

**`region-scout`** (new)
- Resolves region name → primary country ETF ticker
- Pulls top 40 holdings via yfinance
- Groups holdings by GICS sector
- Returns sector baskets (top 5–7 stocks per sector) and the ETF metadata
- Writes `research/{REGION}/scout.json`

**`macro-secular`** (existing, reused as-is)
- Called with the region/country as the subject
- Covers: GDP trajectory, rate/inflation cycle, currency risk, working-age population trend, urbanization, consumption growth
- Writes `research/{REGION}/macro.json`

Wait for both before Stage 2.

### Stage 2 — Sector screeners (parallel)

The command reads `scout.json` after Stage 1 completes to discover the sector list, then dispatches one `sector-screener` agent per sector. All fire in parallel.

Each agent covers the top 5–7 stocks in its sector basket:

**Fundamentals layer (yfinance)**
- P/E, P/B, ROE, revenue growth (1y, 3y), gross margin, EBIT margin, FCF margin
- Scored relative to global sector median benchmarks

**Forecast trend layer (yfinance analyst data)**
- Earnings estimate revisions (last 90 days: up / flat / down)
- Revenue consensus trend
- Analyst recommendation distribution

**News layer (web search, last 90 days)**
- Every item tagged with `source_type`: `filing` | `earnings_call` | `regulator` | `analyst_note` | `media`
- Every item tagged with `confidence`: `high` (filing/regulator) | `medium` (earnings call/analyst note) | `low` (media)
- Agent instruction: a media narrative with no fundamental backing is a **flag**, not a score boost. Surface as "narrative risk."
- Positive media momentum with strong fundamentals = valid signal. Media-only narrative = skepticism note.

Each screener writes `research/{REGION}/sector_{name}.json` with:
- Per-stock scores
- Sector aggregate score (fundamentals, forecast, news — weighted 50/30/20)
- Narrative risks (media-driven claims not backed by numbers)
- Sector-level `edge` boolean with rationale

### Stage 3 — Region synthesizer (sequential)

**`region-synthesizer`** (new) reads all prior files and writes the final brief.

Output: `research/{REGION}/brief.json` + `research/{REGION}/brief.md`

---

## Output: Structured Brief (`brief.md`)

### Part 1 — Macro & Demographic Backdrop
Sourced from `macro.json`. Covers the country-level tailwind/headwind with a plain-language summary. Rates the macro backdrop: **Supportive / Neutral / Headwind**.

### Part 2 — Sector Scorecard

| Sector | Fundamentals | Forecast Trend | News Signal | Narrative Risks | Edge? |
|---|---|---|---|---|---|
| Semiconductors | Strong | Positive | Mixed (hype flagged) | AI demand overstated in media | ✓ |
| Banks | Weak | Flat | Neutral | — | ✗ |
| Consumer | Moderate | Positive | Positive | — | ? |

### Part 3 — Verdict

- **Where the edge is:** plain-language conclusion on which sector(s) have genuine fundamental edge
- **Instruments to consider:** specific ETF tickers (country ETF or sector-within-country ETF)
- **Pass conditions:** explicit "pass" if no sector clears the bar, with reason
- **Watch list:** sectors that missed now but are worth revisiting with a trigger condition

---

## New Files

| File | Type | Purpose |
|---|---|---|
| `long-horizon-investing/commands/scan-region.md` | Command | Entry point, orchestrates the 3 stages |
| `long-horizon-investing/agents/region-scout.md` | Agent | ETF resolution + holdings grouping by sector |
| `long-horizon-investing/agents/sector-screener.md` | Agent | Per-sector fundamentals + forecast + news scoring |
| `long-horizon-investing/agents/region-synthesizer.md` | Agent | Reads all evidence, writes brief.json + brief.md |

**No changes** to existing agents, commands, or skills.

---

## Reused Components

| Component | How reused |
|---|---|
| `macro-secular` agent | Called with region as subject; output already covers FRED demographics/macro |
| `research/{TICKER}/` convention | Same output directory pattern, region slug instead of ticker |
| JSON envelope schema | `sector_{name}.json` follows the same `role/ticker/as_of_date/content` envelope |
| yfinance MCP | Holdings pull, fundamentals, analyst forecasts |
| WebSearch tool | News layer in sector-screener |

---

## Scoring Weights

| Layer | Weight | Rationale |
|---|---|---|
| Fundamentals | 50% | Hard numbers, multi-year, least manipulable |
| Forecast trend | 30% | Forward-looking but analyst-consensus-based |
| News | 20% | Real signal exists but high noise; source-confidence multiplier applied |

News confidence multiplier: `high` = 1.0x, `medium` = 0.6x, `low` = 0.2x. A sector driven purely by low-confidence media gets an effective news weight near zero.

---

## Non-Goals

- No individual stock verdicts or buy/sell signals
- No portfolio sizing or position recommendations
- No backtesting
- No comparison across multiple countries in a single run (run `/scan-region` separately per country)
