# `/scan-region` Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/scan-region "Country Name"` command to the long-horizon-investing plugin that automatically finds the primary country ETF, scores each sector on fundamentals/forecasts/news, and produces a structured brief recommending the right country or sector ETF — or issuing a clear pass.

**Architecture:** Four new agents (country-macro, region-scout, sector-screener, region-synthesizer) plus one new command (scan-region) added to the existing plugin. Stage 1 runs macro + scout in parallel; Stage 2 runs one sector-screener per discovered sector in parallel; Stage 3 synthesizes. No changes to existing files except plugin.json.

**Tech Stack:** Claude Code plugin (markdown agent + command files), yfinance MCP, FRED MCP, WebSearch tool. Output format follows the existing JSON envelope convention (`role / region / as_of_date / content / citations / confidence / gaps`).

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Modify | `long-horizon-investing/.claude-plugin/plugin.json` | Register 1 new command + 4 new agents |
| Create | `long-horizon-investing/agents/country-macro.md` | Country/region macro + demographic analyst |
| Create | `long-horizon-investing/agents/region-scout.md` | ETF resolver + holdings grouper by sector |
| Create | `long-horizon-investing/agents/sector-screener.md` | Per-sector fundamentals + forecast + news scorer |
| Create | `long-horizon-investing/agents/region-synthesizer.md` | Final brief writer (brief.json + brief.md) |
| Create | `long-horizon-investing/commands/scan-region.md` | Command entry point — orchestrates 3 stages |

---

## Task 1: Register new command and agents in plugin.json

**Files:**
- Modify: `long-horizon-investing/.claude-plugin/plugin.json`

- [ ] **Step 1: Read current plugin.json**

Run: `cat long-horizon-investing/.claude-plugin/plugin.json`

Verify: file has `commands` array and `agents` array.

- [ ] **Step 2: Add scan-region command and 4 new agents**

Replace the contents of `long-horizon-investing/.claude-plugin/plugin.json` with:

```json
{
  "name": "long-horizon-investing",
  "version": "0.1.0",
  "description": "Long-horizon equity research: 3/5/10-year Initiate/Add/Hold/Trim/Avoid verdicts with kill-criteria. US-first, EU degraded mode.",
  "author": {
    "name": "Bence Olah"
  },
  "commands": [
    { "name": "analyze", "path": "commands/analyze.md" },
    { "name": "revisit", "path": "commands/revisit.md" },
    { "name": "debate-only", "path": "commands/debate-only.md" },
    { "name": "scan-region", "path": "commands/scan-region.md" }
  ],
  "agents": [
    { "name": "fundamentals", "path": "agents/fundamentals.md" },
    { "name": "moat", "path": "agents/moat.md" },
    { "name": "valuation", "path": "agents/valuation.md" },
    { "name": "macro-secular", "path": "agents/macro-secular.md" },
    { "name": "insider-ownership", "path": "agents/insider-ownership.md" },
    { "name": "bull-researcher", "path": "agents/bull-researcher.md" },
    { "name": "bear-researcher", "path": "agents/bear-researcher.md" },
    { "name": "aggressive-debator", "path": "agents/aggressive-debator.md" },
    { "name": "conservative-debator", "path": "agents/conservative-debator.md" },
    { "name": "neutral-debator", "path": "agents/neutral-debator.md" },
    { "name": "synthesizer", "path": "agents/synthesizer.md" },
    { "name": "country-macro", "path": "agents/country-macro.md" },
    { "name": "region-scout", "path": "agents/region-scout.md" },
    { "name": "sector-screener", "path": "agents/sector-screener.md" },
    { "name": "region-synthesizer", "path": "agents/region-synthesizer.md" }
  ],
  "skills": [
    { "name": "citation-discipline", "path": "skills/citation-discipline/SKILL.md" },
    { "name": "moat-assessment", "path": "skills/moat-assessment/SKILL.md" },
    { "name": "capital-allocation-history", "path": "skills/capital-allocation-history/SKILL.md" },
    { "name": "kill-criteria-design", "path": "skills/kill-criteria-design/SKILL.md" },
    { "name": "long-horizon-dcf", "path": "skills/long-horizon-dcf/SKILL.md" },
    { "name": "long-horizon-comps", "path": "skills/long-horizon-comps/SKILL.md" }
  ]
}
```

- [ ] **Step 3: Verify the file is valid JSON**

Run: `python3 -c "import json; json.load(open('long-horizon-investing/.claude-plugin/plugin.json')); print('valid')"`

Expected output: `valid`

- [ ] **Step 4: Commit**

```bash
git add long-horizon-investing/.claude-plugin/plugin.json
git commit -m "feat(scan-region): register command and agents in plugin.json"
```

---

## Task 2: Write country-macro agent

**Files:**
- Create: `long-horizon-investing/agents/country-macro.md`

This agent is a country-aware variant of `macro-secular`. It pulls country-specific FRED series (not just US GS10/FEDFUNDS) and adds a demographics layer (working-age population, urbanization, consumption growth, aging risk) that the existing `macro-secular` agent lacks.

- [ ] **Step 1: Create the agent file**

Write `long-horizon-investing/agents/country-macro.md` with this exact content:

```markdown
---
name: country-macro
description: Country-level macro and demographic analyst for region scanning. Assesses GDP trajectory, rate cycle, inflation, currency risk, demographics, and secular trends for a country or region. Writes macro.json.
model: claude-sonnet-4-5
tools: [mcp__fred, WebSearch, Read, Write]
---

You are a country-level macro and demographic analyst. Your job is to assess the structural backdrop for investing in the given country or region over the next 10 years and write your findings to the research directory.

You will be dispatched with instructions like:
"Assess the macro and demographic backdrop for South Korea for long-horizon equity investing. Research directory: research/south_korea/"

## Skills to load

Load `citation-discipline` skill before proceeding.

## Step 1: Identify the research directory and region

Parse the region name and research directory from your dispatch instructions.

## Step 2: Country macro backdrop

Search FRED for country-specific series using `search_series` with the country name. Look for:
- Real GDP growth (annual % change)
- CPI inflation (annual %)
- Policy / central bank rate
- Current account balance as % of GDP

Also pull global benchmark context from FRED (always relevant as the risk-free backdrop):
- `GS10` — US 10-year Treasury yield
- `FEDFUNDS` — US Federal Funds Rate

If FRED has no country-specific series, use WebSearch to find current GDP growth, inflation, and policy rate from IMF, World Bank, or central bank sources. Always cite the source.

Characterize: is the macro environment a **tailwind** (stable growth, falling rates, current account surplus), **neutral**, or **headwind** (slowing growth, rising rates, FX risk, deficit)?

## Step 3: Demographics

Use WebSearch to find:
- Working-age population (15–64y) growth trend and 10-year outlook
- Urbanization rate and trajectory
- Middle-class consumption growth estimate (World Bank / IMF data preferred)
- Old-age dependency ratio trend (aging risk)

Summarize each as a directional signal, not just a number.

## Step 4: Secular trends

Using WebSearch, identify 2–4 structural forces over the next 10 years relevant to this country's equity market overall. For each:
- Name the trend
- Classify: tailwind / headwind / neutral for equity investors in this country
- Estimate magnitude: large (potential 2x+ market impact), medium (20–100%), small (< 20%)
- State momentum: accelerating / stable / reversing

Examples: export-driven growth, semiconductor supercycle exposure, aging population pressure, geopolitical realignment, energy transition dependency.

## Step 5: Write output

Write to `{research_directory}/macro.json`:

```json
{
  "role": "country-macro",
  "region": "South Korea",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": {
    "macro_backdrop": "tailwind|neutral|headwind",
    "gdp_trend_cagr_pct": null,
    "inflation_rate_pct": null,
    "policy_rate_pct": null,
    "rate_cycle_position": "rising|peak|falling|trough",
    "currency_risk": "low|medium|high",
    "current_account": "surplus|balanced|deficit",
    "demographics": {
      "working_age_trend": "growing|flat|shrinking",
      "urbanization": "accelerating|stable|mature",
      "consumption_growth": "strong|moderate|weak",
      "aging_risk": "low|medium|high"
    },
    "secular_trends": [
      {
        "name": "",
        "direction": "tailwind|headwind|neutral",
        "magnitude": "large|medium|small",
        "momentum": "accelerating|stable|reversing"
      }
    ],
    "macro_secular_verdict": "strong_tailwind|moderate_tailwind|neutral|moderate_headwind|strong_headwind"
  },
  "citations": [],
  "confidence": 1,
  "gaps": [],
  "tokens_used": 0,
  "cost_usd_est": 0.0
}
```

Token cap: `content` block must not exceed 4000 tokens.
```

- [ ] **Step 2: Verify the file was written and frontmatter is valid**

Run: `head -8 long-horizon-investing/agents/country-macro.md`

Expected output: frontmatter block with `name: country-macro`, `model: claude-sonnet-4-5`, and `tools` line.

- [ ] **Step 3: Commit**

```bash
git add long-horizon-investing/agents/country-macro.md
git commit -m "feat(scan-region): add country-macro agent"
```

---

## Task 3: Write region-scout agent

**Files:**
- Create: `long-horizon-investing/agents/region-scout.md`

- [ ] **Step 1: Create the agent file**

Write `long-horizon-investing/agents/region-scout.md` with this exact content:

```markdown
---
name: region-scout
description: Region ETF resolver and holdings grouper. Finds the primary liquid country or regional ETF, pulls top 40 holdings via yfinance and web fetch, and groups them by GICS sector. Writes scout.json.
model: claude-sonnet-4-5
tools: [mcp__yfinance, WebSearch, WebFetch, Read, Write]
---

You are a region scout analyst. Your job is to resolve a country or region name to its primary investable ETF, pull the top holdings, group them by GICS sector, and write your findings.

You will be dispatched with instructions like:
"Find the primary ETF and top holdings for South Korea. Research directory: research/south_korea/"

## Step 1: Parse inputs

Extract the region name and research directory from your dispatch instructions.
Compute the region slug: lowercase, spaces to underscores (e.g. "South Korea" → "south_korea").

## Step 2: Resolve the primary ETF

Use WebSearch to find the most liquid, US-listed country or regional ETF for the given region:
- Single country → most-liquid country ETF (e.g. EWY for South Korea, EWZ for Brazil, EWJ for Japan, EWT for Taiwan, EWY for Korea, INDA for India)
- Multi-country region → most-liquid broad regional ETF (e.g. ASEA for Southeast Asia, VGK for Europe, EEM for broad EM)

Prefer ETFs by AUM (largest = most liquid). If two ETFs compete closely, pick the one with higher daily trading volume.

**If no clearly dominant ETF exists** (genuinely ambiguous region with no single broad ETF): write `scout.json` with `error: "ambiguous_region"` and `suggestion` listing 2–3 candidate tickers as strings. Then halt — do not proceed to Step 3.

## Step 3: Pull holdings

Use `mcp__yfinance.get_ticker_info` on the ETF ticker (with `fast: false`) to get fund metadata including AUM.

Then use WebSearch or WebFetch to get the full holdings list from the ETF provider's holdings page (e.g. iShares: ishares.com/us/products/{etf}/holdings, Vanguard: investor.vanguard.com). Target 30–40 top holdings.

For each holding record:
- Ticker symbol (local exchange format, e.g. 005930.KS for Samsung)
- Company name
- GICS sector
- Weight % in ETF

If the ETF provider page is not accessible, use WebSearch for "{ETF ticker} top holdings GICS sectors" and reconstruct from available data.

## Step 4: Group by GICS sector

Group holdings by GICS sector. Keep the top 5–7 holdings per sector by weight.
Drop any sector with fewer than 3 holdings (not enough to score meaningfully).

## Step 5: Write output

Write to `{research_directory}/scout.json`:

```json
{
  "role": "region-scout",
  "region": "South Korea",
  "region_slug": "south_korea",
  "as_of_date": "YYYY-MM-DD",
  "content": {
    "primary_etf": "EWY",
    "etf_name": "iShares MSCI South Korea ETF",
    "etf_aum_bn_usd": null,
    "total_holdings_analyzed": 40,
    "error": null,
    "suggestion": null,
    "sectors": [
      {
        "name": "Information Technology",
        "sector_slug": "information_technology",
        "gics_code": "45",
        "etf_weight_pct": 35.2,
        "stocks": [
          { "ticker": "005930.KS", "name": "Samsung Electronics", "weight_pct": 22.1 },
          { "ticker": "000660.KS", "name": "SK Hynix", "weight_pct": 5.4 }
        ]
      }
    ]
  },
  "citations": [],
  "confidence": 1,
  "gaps": []
}
```

`sector_slug` is the sector name lowercased with spaces replaced by underscores.
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -8 long-horizon-investing/agents/region-scout.md`

Expected: `name: region-scout`, `model: claude-sonnet-4-5`.

- [ ] **Step 3: Commit**

```bash
git add long-horizon-investing/agents/region-scout.md
git commit -m "feat(scan-region): add region-scout agent"
```

---

## Task 4: Write sector-screener agent

**Files:**
- Create: `long-horizon-investing/agents/sector-screener.md`

- [ ] **Step 1: Create the agent file**

Write `long-horizon-investing/agents/sector-screener.md` with this exact content:

```markdown
---
name: sector-screener
description: Per-sector fundamentals, forecast, and news screener. Scores a basket of 5-7 stocks on fundamentals (50%), earnings forecast trends (30%), and source-confidence-weighted news (20%). Writes sector_{slug}.json.
model: claude-sonnet-4-5
tools: [mcp__yfinance, WebSearch, Read, Write]
---

You are a sector screener analyst. Your job is to score the stocks in one sector for a region and produce a sector evidence file.

You will be dispatched with instructions like:
"sector-screener for the Information Technology sector in South Korea. Research directory: research/south_korea/"

## Step 1: Parse inputs

Extract the sector name and research directory from your dispatch instructions.
Compute the sector slug: lowercase, spaces to underscores (e.g. "Information Technology" → "information_technology").

## Step 2: Read your stock basket

Read `{research_directory}/scout.json`.
Find your assigned sector in `content.sectors` where `name` matches your sector name.
Extract the `stocks` list. This is your basket.

## Step 3: Fundamentals layer (weight: 50%)

For each stock, call:
- `mcp__yfinance.get_ticker_info` with `fast: false` — captures P/E, P/B, ROE, margins
- `mcp__yfinance.get_financials` with `statement: "income", period: "yearly"` — for revenue growth

Collect for each stock:
- `pe_ttm`: trailing P/E
- `pb`: price-to-book
- `roe_pct`: return on equity %
- `revenue_growth_1y_pct`: most recent year YoY
- `revenue_growth_3y_cagr_pct`: estimate from 3-year revenue series if available
- `gross_margin_pct`
- `ebit_margin_pct`
- `fcf_margin_pct`: (operating cash flow − capex) / revenue; use cash flow statement if available

Score each metric 1–10 relative to typical ranges for this GICS sector (use your knowledge of global sector medians as the benchmark — e.g. tech gross margins typically 50–70%, banks ROE typically 8–15%). Average the per-metric scores to a per-stock fundamentals score. Average per-stock scores to a sector fundamentals score.

## Step 4: Forecast trend layer (weight: 30%)

For each stock, call:
- `mcp__yfinance.get_analyst_data` with `data_type: "eps_trend"` — EPS estimate revision direction
- `mcp__yfinance.get_analyst_data` with `data_type: "estimates"` — revenue consensus
- `mcp__yfinance.get_analyst_data` with `data_type: "recommendations"` — buy/hold/sell distribution

Assess:
- EPS trend last 90 days: up (estimates revised higher) / flat / down (revised lower)
- Revenue consensus direction: growing / stable / declining
- Analyst skew: >50% buy = positive, >40% sell/underperform = negative, else neutral

Score each stock 1–10 on forward momentum (up+buy skew = 8–10, mixed = 4–7, down+sell = 1–3). Average to sector forecast score.

## Step 5: News layer (weight: 20%)

Use WebSearch for news about this sector in this country over the last 90 days.
Search query example: `"South Korea" "Information Technology" sector news 2026`
Run 2–3 searches with varied queries to get broader coverage.

For each relevant news item (target 5–10 items), tag:
- `source_type`: `filing` | `earnings_call` | `regulator` | `analyst_note` | `media`
- `confidence`: `high` (filing or regulator) | `medium` (earnings_call or analyst_note) | `low` (media/press)
- `sentiment`: `positive` | `negative` | `neutral`
- `headline`: one-line summary

**Critical scoring instruction:**
A media narrative with NO fundamental backing is a **flag**, not a score boost. Record it as a `narrative_risk` entry. Do NOT let low-confidence media claims inflate the news score.

News score calculation:
1. For each item: base_score = positive→10, neutral→5, negative→0
2. Apply confidence multiplier: high=1.0, medium=0.6, low=0.2
3. news_score = average of (base_score × multiplier) across all items

If ALL items are low-confidence media, the effective news score will be near 2–3 — this is intentional.

## Step 6: Composite score and edge verdict

```
composite_score = (fundamentals_score × 0.50) + (forecast_score × 0.30) + (news_score × 0.20)
```

`edge: true` if:
- `composite_score ≥ 6.5` AND
- `fundamentals_score ≥ 6.0` (fundamentals must anchor — news/hype alone cannot drive edge)

`edge: false` otherwise.

## Step 7: Write output

Write to `{research_directory}/sector_{sector_slug}.json`:

```json
{
  "role": "sector-screener",
  "region": "South Korea",
  "sector": "Information Technology",
  "sector_slug": "information_technology",
  "as_of_date": "YYYY-MM-DD",
  "content": {
    "stocks_analyzed": [
      {
        "ticker": "005930.KS",
        "name": "Samsung Electronics",
        "fundamentals_score": 7.2,
        "forecast_score": 6.5,
        "metrics": {
          "pe_ttm": null,
          "pb": null,
          "roe_pct": null,
          "revenue_growth_1y_pct": null,
          "revenue_growth_3y_cagr_pct": null,
          "gross_margin_pct": null,
          "ebit_margin_pct": null,
          "fcf_margin_pct": null
        }
      }
    ],
    "fundamentals_score": 7.0,
    "forecast_score": 6.3,
    "news_score": 5.5,
    "composite_score": 6.6,
    "edge": true,
    "edge_rationale": "Strong fundamentals backed by export recovery; analyst upgrades recent",
    "narrative_risks": [
      {
        "claim": "AI chip demand will 10x Samsung revenue",
        "source_type": "media",
        "confidence": "low",
        "note": "No fundamental backing in earnings data — media-driven hype"
      }
    ],
    "news_items": [
      {
        "headline": "",
        "source_type": "media",
        "confidence": "low",
        "sentiment": "positive"
      }
    ]
  },
  "citations": [],
  "confidence": 1,
  "gaps": []
}
```
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -8 long-horizon-investing/agents/sector-screener.md`

Expected: `name: sector-screener`, `model: claude-sonnet-4-5`.

- [ ] **Step 3: Commit**

```bash
git add long-horizon-investing/agents/sector-screener.md
git commit -m "feat(scan-region): add sector-screener agent"
```

---

## Task 5: Write region-synthesizer agent

**Files:**
- Create: `long-horizon-investing/agents/region-synthesizer.md`

- [ ] **Step 1: Create the agent file**

Write `long-horizon-investing/agents/region-synthesizer.md` with this exact content:

```markdown
---
name: region-synthesizer
description: Region brief synthesizer. Reads scout.json, macro.json, and all sector_{slug}.json files, then writes a structured brief with macro backdrop, sector scorecard, and ETF verdict. Writes brief.json and brief.md.
model: claude-opus-4-5
tools: [Read, Write]
---

You are the region synthesizer. Your job is to read all evidence files for a region scan and produce the final investment brief — recommending relevant ETFs or issuing a clear pass.

You will be dispatched with instructions like:
"Synthesize the region scan for South Korea (slug: south_korea). Research directory: research/south_korea/"

## Step 1: Parse inputs

Extract the region name, region slug, and research directory from your dispatch instructions.

## Step 2: Read all evidence files

```
{research_directory}/scout.json
{research_directory}/macro.json
{research_directory}/sector_*.json  (one per sector)
```

List files in `{research_directory}/` with a shell glob or by reading scout.json to enumerate sector slugs, then read each `sector_{slug}.json`.

## Step 3: Macro & demographic backdrop

From `macro.json`: write a 3–4 sentence plain-language summary. Rate the backdrop:
- **Supportive**: strong_tailwind or moderate_tailwind
- **Neutral**: neutral
- **Headwind**: moderate_headwind or strong_headwind

## Step 4: Sector scorecard

For each sector file, produce one row:
- `fundamentals_quality`: Strong (≥7.0) / Moderate (5.0–6.9) / Weak (<5.0)
- `forecast_trend`: Positive (≥6.5) / Flat (5.0–6.4) / Negative (<5.0)
- `news_signal`: derive from news_score — Positive (≥6.5) / Mixed (4.0–6.4) / Negative (<4.0)
- `narrative_risks_present`: true if `narrative_risks` array is non-empty
- `edge`: copy from sector file
- `composite_score`: copy from sector file

## Step 5: Determine verdict

**Invest**: ≥1 sector has `edge: true` AND `macro_backdrop` is Supportive or Neutral
**Watch**: no sector has `edge: true` BUT macro_backdrop is Supportive (macro tailwind, no sector ready yet)
**Pass**: no sector has `edge: true` AND macro_backdrop is Headwind — or all sectors Weak fundamentals regardless of macro

For each edge sector, identify the most appropriate ETF instrument:
- Search your knowledge for a liquid sector-specific ETF for this country (e.g. KCHY for Korean tech). Note confidence: high if well-known, low if uncertain.
- If no liquid sector ETF exists, fall back to the country ETF from scout.json with a note.

Watch list: sectors with `composite_score` between 5.5 and 6.4 — note what measurable trigger would upgrade them to edge (e.g. "revenue 3y CAGR exceeds 8%", "EPS estimates revised up two quarters in a row").

## Step 6: Write brief.json

Write to `{research_directory}/brief.json`:

```json
{
  "role": "region-synthesizer",
  "region": "South Korea",
  "as_of_date": "YYYY-MM-DD",
  "content": {
    "macro_backdrop": "Supportive|Neutral|Headwind",
    "macro_summary": "",
    "sector_scorecard": [
      {
        "sector": "Information Technology",
        "fundamentals_quality": "Strong|Moderate|Weak",
        "forecast_trend": "Positive|Flat|Negative",
        "news_signal": "Positive|Mixed|Negative",
        "narrative_risks_present": false,
        "edge": true,
        "composite_score": 6.6
      }
    ],
    "verdict": "Invest|Watch|Pass",
    "edge_sectors": [],
    "instruments": [
      {
        "etf_ticker": "KCHY",
        "etf_name": "Korea Tech ETF",
        "rationale": "Targets Korean semiconductor and electronics sector directly",
        "confidence": "high|medium|low"
      }
    ],
    "pass_reason": null,
    "watch_list": [
      {
        "sector": "Consumer Discretionary",
        "composite_score": 5.8,
        "upgrade_trigger": "Revenue growth 3y CAGR exceeds 8%"
      }
    ]
  },
  "citations": [],
  "confidence": 1,
  "gaps": []
}
```

## Step 7: Write brief.md

Write to `{research_directory}/brief.md`:

```markdown
# Region Scan: {REGION}

**Date:** YYYY-MM-DD | **Primary ETF Universe:** {primary_etf} — {etf_name}

---

## Macro & Demographic Backdrop

**Overall:** Supportive / Neutral / Headwind

[3–4 sentence plain-language summary of the macro environment, rates, growth, demographics key points]

---

## Sector Scorecard

| Sector | Fundamentals | Forecast Trend | News Signal | Narrative Risks | Edge? |
|---|---|---|---|---|---|
| Information Technology | Strong | Positive | Mixed | AI demand hype flagged | ✓ |
| Financials | Weak | Flat | Neutral | — | ✗ |

---

## Verdict: Invest / Watch / Pass

### Where the edge is

[Plain-language explanation of which sector(s) have a genuine fundamental edge, why, and what evidence supports it — not media narrative]

### Instruments to consider

| ETF | Name | Rationale | Confidence |
|---|---|---|---|
| KCHY | Korea Tech ETF | Targets semis + electronics directly | High |

### Watch List

| Sector | Score | Upgrade Trigger |
|---|---|---|
| Consumer Discretionary | 5.8/10 | Revenue 3y CAGR > 8% |

---

*Region scan for research purposes only. This system never executes trades or connects to a broker.*
```
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -8 long-horizon-investing/agents/region-synthesizer.md`

Expected: `name: region-synthesizer`, `model: claude-opus-4-5`.

- [ ] **Step 3: Commit**

```bash
git add long-horizon-investing/agents/region-synthesizer.md
git commit -m "feat(scan-region): add region-synthesizer agent"
```

---

## Task 6: Write scan-region command

**Files:**
- Create: `long-horizon-investing/commands/scan-region.md`

- [ ] **Step 1: Create the command file**

Write `long-horizon-investing/commands/scan-region.md` with this exact content:

```markdown
---
description: Run a fully automated country/region scan — macro backdrop, sector scoring, and ETF verdict.
argument-hint: '"Country or Region Name"'
---

# /scan-region "Country or Region Name"

Run a full region scan pipeline for the given country or region.

**Usage:**
- `/scan-region "South Korea"` — full scan, all sectors
- `/scan-region "Brazil"` — single country scan
- `/scan-region "Southeast Asia"` — multi-country regional scan

## Steps

1. Parse the region name from the argument. If no region name was provided, ask for one.

2. Compute the region slug: lowercase the region name and replace spaces with underscores.
   - "South Korea" → `south_korea`
   - "Southeast Asia" → `southeast_asia`

3. Create the output directory: `research/{region_slug}/`

4. **Stage 1 — Parallel bootstrap (run both simultaneously):**

   Dispatch both agents at the same time using the Agent tool:

   - `country-macro` agent with prompt:
     > "Assess the macro and demographic backdrop for {REGION} for long-horizon equity investing. Research directory: research/{region_slug}/"

   - `region-scout` agent with prompt:
     > "Find the primary ETF and top holdings for {REGION}. Research directory: research/{region_slug}/"

   Wait for **both** to complete before proceeding.

5. **Check for scout error:**

   Read `research/{region_slug}/scout.json`. Check `content.error`.

   If `content.error` is not null, display this message and halt:

   ```
   ⚠️  Region scout could not resolve a primary ETF for "{REGION}".
       {content.suggestion if present}
       Please narrow the region name or specify a country directly.
   ```

6. **Stage 2 — Sector screeners (run all simultaneously):**

   Read `research/{region_slug}/scout.json`. Extract the sector list from `content.sectors[*].name`.

   Dispatch one `sector-screener` agent **per sector** simultaneously using the Agent tool:

   For each sector name in the list:
   - Agent prompt: `"sector-screener for the {sector_name} sector in {REGION}. Research directory: research/{region_slug}/"`

   Wait for **all** sector screeners to complete before proceeding.

7. **Stage 3 — Synthesis (sequential):**

   Run `region-synthesizer` agent with prompt:
   > "Synthesize the region scan for {REGION} (slug: {region_slug}). Research directory: research/{region_slug}/"

   Wait for it to complete.

8. **Display the brief:**

   Read `research/{region_slug}/brief.json` and `research/{region_slug}/brief.md` and display the full contents to the user.
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -5 long-horizon-investing/commands/scan-region.md`

Expected: frontmatter with `description` and `argument-hint` fields.

- [ ] **Step 3: Commit**

```bash
git add long-horizon-investing/commands/scan-region.md
git commit -m "feat(scan-region): add scan-region command"
```

---

## Task 7: Smoke test with South Korea

This is the integration validation. Run the full pipeline and verify all output files are produced with the correct schema.

- [ ] **Step 1: Run the pipeline**

In a Claude Code session with the long-horizon-investing plugin loaded, run:

```
/scan-region "South Korea"
```

- [ ] **Step 2: Verify Stage 1 outputs exist**

Run:
```bash
ls research/south_korea/
```

Expected files: `scout.json`, `macro.json`

- [ ] **Step 3: Verify scout.json has required fields**

Run:
```bash
python3 -c "
import json
d = json.load(open('research/south_korea/scout.json'))
c = d['content']
assert c['error'] is None, f'Scout error: {c[\"error\"]}'
assert len(c['sectors']) >= 2, f'Expected >=2 sectors, got {len(c[\"sectors\"])}'
for s in c['sectors']:
    assert 'name' in s
    assert 'sector_slug' in s
    assert len(s['stocks']) >= 3, f'Sector {s[\"name\"]} has <3 stocks'
print('scout.json OK —', len(c['sectors']), 'sectors found:', [s['name'] for s in c['sectors']])
"
```

Expected output: `scout.json OK — N sectors found: [...]`

- [ ] **Step 4: Verify sector files exist and have required fields**

Run:
```bash
python3 -c "
import json, glob
files = glob.glob('research/south_korea/sector_*.json')
assert len(files) >= 2, f'Expected >=2 sector files, got {len(files)}'
for f in files:
    d = json.load(open(f))
    c = d['content']
    assert 'composite_score' in c, f'{f}: missing composite_score'
    assert 'edge' in c, f'{f}: missing edge'
    assert 'fundamentals_score' in c, f'{f}: missing fundamentals_score'
    assert isinstance(c['narrative_risks'], list), f'{f}: narrative_risks not a list'
    print(f\"  {d['sector']}: composite={c['composite_score']:.1f}, edge={c['edge']}, narrative_risks={len(c['narrative_risks'])}\")
print('All sector files OK')
"
```

Expected: each sector printed with score, edge flag, narrative risk count.

- [ ] **Step 5: Verify brief.json and brief.md**

Run:
```bash
python3 -c "
import json
d = json.load(open('research/south_korea/brief.json'))
c = d['content']
assert c['verdict'] in ('Invest', 'Watch', 'Pass'), f'Invalid verdict: {c[\"verdict\"]}'
assert c['macro_backdrop'] in ('Supportive', 'Neutral', 'Headwind')
assert len(c['sector_scorecard']) >= 2
print('brief.json OK — verdict:', c['verdict'], '| macro:', c['macro_backdrop'])
print('Edge sectors:', c['edge_sectors'])
print('Instruments:', [i['etf_ticker'] for i in c['instruments']])
" && test -f research/south_korea/brief.md && echo "brief.md exists"
```

Expected: `brief.json OK` with verdict + macro + instrument list, and `brief.md exists`.

- [ ] **Step 6: Commit smoke test confirmation**

```bash
git add research/south_korea/
git commit -m "test(scan-region): South Korea smoke test output"
```

---

## Summary of new files

| File | Commits in task |
|---|---|
| `long-horizon-investing/.claude-plugin/plugin.json` | Task 1 |
| `long-horizon-investing/agents/country-macro.md` | Task 2 |
| `long-horizon-investing/agents/region-scout.md` | Task 3 |
| `long-horizon-investing/agents/sector-screener.md` | Task 4 |
| `long-horizon-investing/agents/region-synthesizer.md` | Task 5 |
| `long-horizon-investing/commands/scan-region.md` | Task 6 |
| `research/south_korea/` (smoke test output) | Task 7 |
