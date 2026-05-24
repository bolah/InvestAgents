# Long-Horizon Investing Plugin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude-Code-runnable plugin that analyzes a single equity ticker for 3/5/10-year horizons via a 4-stage parallel subagent pipeline (5 analysts → 2 researchers → 3 risk debators → 1 synthesizer), producing an Initiate/Add/Hold/Trim/Avoid verdict backed by kill-criteria.

**Architecture:** Root command `/analyze TICKER` dispatches Claude Code subagents in parallel stages. All inter-agent data lives in `research/{TICKER}/*.json` files (shared state, not conversation); the synthesizer reads all of them and writes `verdict.json` + `report.md`. No LangGraph, no brokers, no trade execution.

**Tech Stack:** Claude Code plugin system (`.claude-plugin/plugin.json`, `agents/`, `commands/`, `skills/`), MCP servers (EdgarTools, yfinance, FRED), Markdown agent definitions, JSON schemas.

**Source attribution:** Assets adapted from `github.com/anthropics/financial-services` (Apache-2.0) and `github.com/bolah/InvestAgents` (Apache-2.0). All ported files carry attribution headers per spec §10.

---

## File Map

All files are **new** unless noted. Root = `long-horizon-investing/`.

| File | Responsibility |
|---|---|
| `.claude-plugin/plugin.json` | Plugin manifest — name, version, commands, agents, skills |
| `.mcp.json` | MCP server declarations (edgartools, yfinance, fred) |
| `.gitignore` | Excludes `research/` from version control |
| `LICENSE` | Apache-2.0 verbatim |
| `NOTICE` | Attribution to financial-services and InvestAgents |
| `README.md` | Install and usage guide |
| `commands/analyze.md` | `/analyze TICKER` — root orchestrator command |
| `commands/revisit.md` | `/revisit TICKER` — re-evaluate kill-criteria from `history.md` |
| `commands/debate-only.md` | `/debate-only TICKER` — run debate stages from existing analyst files |
| `agents/fundamentals.md` | Fundamentals analyst subagent (EDGAR/yfinance) |
| `agents/moat.md` | Moat analyst subagent (EDGAR + web) |
| `agents/valuation.md` | Valuation analyst subagent (EDGAR + yfinance + FRED) |
| `agents/macro-secular.md` | Macro & secular analyst subagent (FRED + web) |
| `agents/insider-ownership.md` | Insider & institutional ownership subagent (EDGAR Form 4/13F) |
| `agents/bull-researcher.md` | Bull researcher subagent (reads all analyst files) |
| `agents/bear-researcher.md` | Bear researcher subagent (reads all analyst files) |
| `agents/aggressive-debator.md` | Aggressive risk debator (reads analysts + bull + bear) |
| `agents/conservative-debator.md` | Conservative risk debator (reads analysts + bull + bear) |
| `agents/neutral-debator.md` | Neutral risk debator (reads analysts + bull + bear) |
| `agents/synthesizer.md` | Synthesizer subagent — reads all, writes verdict.json + report.md |
| `skills/citation-discipline/SKILL.md` | Cross-cutting: cite or flag, never fabricate |
| `skills/moat-assessment/SKILL.md` | Morningstar 5-source moat taxonomy |
| `skills/capital-allocation-history/SKILL.md` | Capital allocation assessment framework |
| `skills/kill-criteria-design/SKILL.md` | Kill-criteria specification framework |
| `skills/long-horizon-dcf/SKILL.md` | Normalized-earnings DCF (adapted from financial-analysis/dcf-model) |
| `skills/long-horizon-comps/SKILL.md` | Through-cycle comps (adapted from financial-analysis/comps-analysis) |
| `samples/COST/` | Committed worked example — one complete ticker run |

---

## Task 1: Repo scaffold — legal, plugin manifest, MCP

**Files:**
- Create: `long-horizon-investing/LICENSE`
- Create: `long-horizon-investing/NOTICE`
- Create: `long-horizon-investing/.gitignore`
- Create: `long-horizon-investing/.claude-plugin/plugin.json`
- Create: `long-horizon-investing/.mcp.json`

- [ ] **Step 1: Create the repo directory and LICENSE**

```bash
mkdir -p long-horizon-investing/.claude-plugin
mkdir -p long-horizon-investing/commands
mkdir -p long-horizon-investing/agents
mkdir -p long-horizon-investing/skills/citation-discipline
mkdir -p long-horizon-investing/skills/moat-assessment
mkdir -p long-horizon-investing/skills/capital-allocation-history
mkdir -p long-horizon-investing/skills/kill-criteria-design
mkdir -p long-horizon-investing/skills/long-horizon-dcf
mkdir -p long-horizon-investing/skills/long-horizon-comps
mkdir -p long-horizon-investing/samples
```

Copy the Apache-2.0 license verbatim into `long-horizon-investing/LICENSE`:
```
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION
   ... (full Apache-2.0 text — copy from https://www.apache.org/licenses/LICENSE-2.0.txt)
```

- [ ] **Step 2: Create NOTICE**

```
long-horizon-investing — Long-Horizon Equity Research Plugin
Copyright 2026 Bence Olah

This product includes software adapted from:

  financial-services — Anthropic FSI Reference Plugins
  Copyright 2024 Anthropic
  Licensed under the Apache License, Version 2.0
  Source: https://github.com/anthropics/financial-services
  Modified files: skills/long-horizon-dcf/SKILL.md,
                  skills/long-horizon-comps/SKILL.md

  InvestAgents — LangGraph Trading Agent System
  Copyright 2024 Bence Olah
  Licensed under the Apache License, Version 2.0
  Source: https://github.com/bolah/InvestAgents
  Modified files: agents/bull-researcher.md, agents/bear-researcher.md,
                  agents/aggressive-debator.md, agents/conservative-debator.md,
                  agents/neutral-debator.md, agents/synthesizer.md
```

- [ ] **Step 3: Create .gitignore**

```
# Live research runs — never commit (audit trail stays local)
research/

# OS
.DS_Store
```

- [ ] **Step 4: Create plugin.json**

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
    { "name": "debate-only", "path": "commands/debate-only.md" }
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
    { "name": "synthesizer", "path": "agents/synthesizer.md" }
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

- [ ] **Step 5: Create .mcp.json**

```json
{
  "mcpServers": {
    "edgartools": {
      "command": "uvx",
      "args": ["edgartools-mcp"],
      "description": "US SEC EDGAR filings, Form 4 insider transactions, 13F institutional holdings, DEF 14A compensation data. US tickers only."
    },
    "yfinance": {
      "command": "uvx",
      "args": ["yfinance-mcp"],
      "description": "Price history, dividends, buybacks, basic financials. US and EU tickers. EU fundamentals are thin — use for price/multiple history only."
    },
    "fred": {
      "command": "uvx",
      "args": ["fredapi-mcp"],
      "env": {
        "FRED_API_KEY": "${FRED_API_KEY}"
      },
      "description": "FRED macro data: risk-free rates, inflation, yield curve, GDP. Requires free FRED_API_KEY env var."
    }
  }
}
```

- [ ] **Step 6: Commit**

```bash
cd long-horizon-investing
git init
git add .
git commit -m "chore: scaffold repo — LICENSE, NOTICE, plugin.json, .mcp.json, .gitignore"
```

---

## Task 2: Cross-cutting skill — citation discipline

**Files:**
- Create: `skills/citation-discipline/SKILL.md`

This skill is loaded by every analyst and researcher agent. It enforces: cite every number or flag the gap — never fabricate.

- [ ] **Step 1: Write the skill**

```markdown
---
name: citation-discipline
description: Enforce citation-or-flag discipline for all numerical claims in research outputs. Load this skill in every agent that writes to a research envelope file.
---

# Citation Discipline

## The Rule

Every numerical claim written to the `content` block of a research envelope MUST have a corresponding entry in the `citations[]` array.

If you cannot cite a number — because the MCP tool returned no data, the ticker is EU-only and EDGAR is unavailable, or the source is ambiguous — you MUST:

1. Write the gap to the `gaps[]` array: `"data not available: <what and why>"`
2. Omit the number from `content` entirely
3. Never substitute a plausible estimate, a rounded figure, or a "typically around X" guess

## What counts as a numerical claim

- Any revenue, earnings, margin, multiple, ratio, growth rate, yield, or price
- Any date range used in trend statements ("over the past 10 years...")
- Any ranking or market-share figure

## Citation format

Each entry in `citations[]`:
```json
{
  "claim": "10-year average ROIC = 18.3%",
  "source": "edgar",
  "url_or_id": "COST 10-K 2024, SEC CIK 895126",
  "retrieved_at": "2026-05-24"
}
```

Valid `source` values: `edgar`, `yfinance`, `fred`, `web`, `tool`.

## EU mode

If the ticker is not listed on a US exchange and EdgarTools returns no filings:
- Set `eu_mode_degraded: true` at the envelope top level
- Add to `gaps[]`: `"EU mode: EDGAR unavailable; insider/13F data absent; fundamentals from yfinance only"`
- Do NOT fabricate EDGAR-equivalent numbers from yfinance

## Self-check before writing the file

Before writing the envelope JSON, run this mental checklist:
1. Every number in `content` has a matching `citations[]` entry — yes/no?
2. Every unavailable data point is in `gaps[]` — yes/no?
3. `confidence` reflects how much of `content` is cited vs. estimated — scored accordingly

If any answer is no, fix it before writing.
```

- [ ] **Step 2: Commit**

```bash
git add skills/citation-discipline/SKILL.md
git commit -m "feat: add citation-discipline cross-cutting skill"
```

---

## Task 3: Core skills — moat, capital allocation, kill-criteria

**Files:**
- Create: `skills/moat-assessment/SKILL.md`
- Create: `skills/capital-allocation-history/SKILL.md`
- Create: `skills/kill-criteria-design/SKILL.md`

- [ ] **Step 1: Write moat-assessment skill**

```markdown
---
name: moat-assessment
description: Assess a company's competitive moat using Morningstar's 5-source taxonomy. Produces a structured moat section for the moat envelope file.
---

# Moat Assessment

## The 5 Sources of Moat (Morningstar Taxonomy)

Score each source 0 (absent), 1 (weak/narrow), or 2 (strong/wide). A total ≥ 6 = wide moat; 3–5 = narrow moat; < 3 = no moat.

| Source | Description | Evidence to look for |
|---|---|---|
| **Network effects** | Value grows with users/participants | Platform GMV concentration, switching costs from ecosystem lock-in |
| **Intangible assets** | Brands, patents, regulatory licenses | Pricing power vs. generics, trademark/patent counts, licensing revenue |
| **Cost advantage** | Structural cost lead over competitors | Gross margin vs. sector median over 10y; supply-chain scale; proprietary process |
| **Switching costs** | Customer stickiness beyond satisfaction | Churn data, NPS proxies, ERP/workflow integration depth, long-term contracts |
| **Efficient scale** | Serving a market too small for profitable duopetition | Market share in a niche; competitor ROICs vs. cost of capital |

## Assessment Process

1. Pull 10-K Management Discussion & Analysis sections (EDGAR) — look for how management describes pricing power and competitive position.
2. Pull 10 years of gross margin and ROIC data (EDGAR + yfinance) — sustained ROIC > WACC is the empirical moat signal.
3. Run a web search for analyst moat assessments, Morningstar moat ratings if available, and competitor positioning.
4. Score each source with evidence. Cite every score.
5. State the overall moat verdict: wide / narrow / none, with a one-sentence rationale.

## Output block (goes into moat.json `content`)

```json
{
  "moat_verdict": "wide|narrow|none",
  "moat_score_total": 0-10,
  "sources": {
    "network_effects": { "score": 0-2, "evidence": "..." },
    "intangible_assets": { "score": 0-2, "evidence": "..." },
    "cost_advantage": { "score": 0-2, "evidence": "..." },
    "switching_costs": { "score": 0-2, "evidence": "..." },
    "efficient_scale": { "score": 0-2, "evidence": "..." }
  },
  "roic_10y_avg": null,
  "roic_trend": "improving|stable|declining|insufficient_data",
  "moat_durability_horizon": "< 5y|5-10y|> 10y|unknown"
}
```
```

- [ ] **Step 2: Write capital-allocation-history skill**

```markdown
---
name: capital-allocation-history
description: Assess a company's capital allocation track record over 10+ years for long-horizon investing. Covers reinvestment rate, ROIC trend, buyback discipline, and dividend policy.
---

# Capital Allocation History

## Why It Matters at Long Horizons

At a 10-year horizon, capital allocation quality compounds. A management team that earns 20% ROIC on reinvestment doubles intrinsic value in 3.6 years. One that earns cost of capital destroys it through dilutive acquisitions or value-destroying buybacks at peak.

## What to Assess

### 1. Reinvestment rate and ROIC (10y series)
- Pull capex + R&D + net acquisitions as % of EBITDA or operating cash flow (EDGAR 10-K)
- Compute ROIC each year: NOPAT / Invested Capital
- Label each year: value-creating (ROIC > WACC), neutral, or value-destroying

### 2. Buyback discipline
- Pull share count history (10y via yfinance or EDGAR)
- Flag: was buyback timing counter-cyclical (good) or pro-cyclical at peak multiples (bad)?
- Compute average P/E or EV/EBITDA at buyback periods vs. normalized multiple

### 3. Dividend policy
- Pull dividend history via yfinance (10y)
- Classify: no dividend / growing / stable / variable / cut history

### 4. Acquisition track record
- Pull major acquisitions from EDGAR 10-K history and web search
- Assess: did each deal grow or shrink ROIC in the 3 years after close?

### 5. Management skin in the game
- Check insider ownership % (DEF 14A via EDGAR)
- Flag if management holds > 5% of outstanding shares (strong alignment)

## Output block (goes into fundamentals.json `content.capital_allocation`)

```json
{
  "reinvestment_rate_avg_pct": null,
  "roic_10y_series": [],
  "roic_vs_wacc_verdict": "consistently_above|mixed|consistently_below|insufficient_data",
  "buyback_discipline": "counter_cyclical|neutral|pro_cyclical|no_buybacks",
  "dividend_policy": "growing|stable|variable|no_dividend|cut_history",
  "acquisition_track_record": "value_additive|neutral|value_destructive|no_acquisitions",
  "mgmt_insider_ownership_pct": null
}
```
```

- [ ] **Step 3: Write kill-criteria-design skill**

```markdown
---
name: kill-criteria-design
description: Design testable kill-criteria for a long-horizon equity position. Kill-criteria specify the conditions that would prove the investment thesis wrong and trigger a sell review.
---

# Kill-Criteria Design

## The Problem Kill-Criteria Solve

A long-horizon thesis is not falsifiable by quarterly noise. But "I'll hold indefinitely" is not a thesis — it is anchoring. Kill-criteria define in advance what would prove the thesis wrong, making the position intellectually honest and bounded.

## Properties of Good Kill-Criteria

1. **Lagging, not leading** — based on observable facts (revenue decline, ROIC drop, market share loss), not stock price or analyst opinion
2. **Specific and measurable** — "ROIC drops below cost of capital for 2 consecutive years" not "business deteriorates"
3. **Testable on a schedule** — quarterly (financials) or annual (strategic assessments)
4. **Thesis-linked** — each criterion maps to a specific claim in the bull thesis. If the thesis says "cost advantage drives 200bps gross margin lead", the kill-criterion is "gross margin advantage vs. sector narrows to < 50bps for 4 consecutive quarters"

## Standard Kill-Criteria Templates

For each of the following thesis pillars, if relevant, define a kill-criterion:

| Pillar | Template trigger | Lagging indicator |
|---|---|---|
| Moat durability | "Gross margin advantage vs. sector < [X]bps for [N] quarters" | EDGAR filings |
| ROIC quality | "ROIC < WACC for 2 consecutive fiscal years" | EDGAR 10-K |
| Reinvestment runway | "Organic revenue growth < [X]% for 3 consecutive years in core market" | EDGAR + yfinance |
| Capital allocation | "Company executes acquisition > 2x trailing EV at ROIC < 8% implied" | EDGAR 8-K |
| Balance sheet | "Net debt / EBITDA > [X]x and FCF yield < [Y]% simultaneously" | EDGAR 10-Q |
| Secular trend | "TAM growth consensus estimate revised below [X]% CAGR" | Web/analyst consensus |
| Management | "CEO/CFO both depart within 12 months without succession plan" | Web/press |

## Output format (goes into verdict.json `kill_criteria[]`)

```json
{
  "trigger": "ROIC falls below WACC for 2 consecutive fiscal years",
  "lagging_indicator": "EDGAR 10-K: NOPAT / invested capital < 8.5% (estimated WACC) in FY25 and FY26",
  "review_cadence": "annual"
}
```

Write 3–6 kill-criteria. Fewer is better if each one is precise. Vague kill-criteria are worse than none.
```

- [ ] **Step 4: Commit**

```bash
git add skills/moat-assessment/SKILL.md skills/capital-allocation-history/SKILL.md skills/kill-criteria-design/SKILL.md
git commit -m "feat: add moat-assessment, capital-allocation-history, kill-criteria-design skills"
```

---

## Task 4: Adapted skills — long-horizon DCF and comps

**Files:**
- Create: `skills/long-horizon-dcf/SKILL.md` (adapted from financial-analysis/dcf-model)
- Create: `skills/long-horizon-comps/SKILL.md` (adapted from financial-analysis/comps-analysis)

- [ ] **Step 1: Write long-horizon-dcf skill**

Note: `# Modified from financial-analysis/skills/dcf-model/SKILL.md (Apache-2.0). See NOTICE.`

```markdown
---
name: long-horizon-dcf
description: Terminal-value-driven DCF for long-horizon equity valuation. Uses normalized 10-year average earnings power as the base case — not TTM or next-quarter consensus. Outputs a valuation range (bear/base/bull) with sensitivity to terminal growth rate and WACC. No Excel output — produces a JSON valuation block.
---
# Modified from financial-analysis/skills/dcf-model/SKILL.md (Apache-2.0). See NOTICE.

# Long-Horizon DCF

## Key Differences from a Standard DCF

**Standard (short-term) DCF:** anchors to TTM or next-12-month earnings; builds 3-year detailed forecasts; terminal value is an afterthought.

**This DCF:** terminal value is the thesis. The base case is normalized earnings power — the through-cycle average of the last 10 years, adjusted for structural change. Quarterly noise is explicitly excluded.

## Step-by-step

### 1. Derive normalized earnings power
- Pull 10 years of revenue, EBIT margin, and FCF from EDGAR (10-K)
- Compute median EBIT margin over 10y (use median, not mean — more robust to one-off write-offs)
- Apply median margin to current revenue to get "normalized EBIT"
- Normalize for D&A vs. capex spread (maintenance capex, not growth capex)
- Output: `normalized_fcf_per_share` — this is your year-1 DCF anchor

### 2. Estimate WACC
- Risk-free rate: 10-year US Treasury yield from FRED (`GS10` series)
- Equity risk premium: use 5.5% (Damodaran US ERP — cite as "Damodaran 2024 ERP estimate")
- Beta: 5-year monthly beta from yfinance
- Cost of debt: latest interest expense / average debt balance (EDGAR)
- Capital structure weights: from EDGAR balance sheet
- WACC = Ke × (E/V) + Kd × (1-t) × (D/V)

### 3. Build three terminal growth scenarios

| Scenario | Terminal g | Rationale |
|---|---|---|
| Bear | GDP - 1% (approx 1%) | Business matures below GDP |
| Base | GDP (approx 2.5%) | In-line secular growth |
| Bull | GDP + sector premium (approx 4%) | Moat + reinvestment sustains above-GDP |

Use GDP trend from FRED (`GDPC1` 10y CAGR).

### 4. Compute intrinsic value per share

```
Terminal Value = Normalized FCF × (1 + g) / (WACC - g)
IV/share = Terminal Value / Shares Outstanding
```

No multi-year explicit forecast period (adds false precision at long horizons). The terminal value IS the valuation.

### 5. Compute margin of safety

```
Margin of Safety = (IV/share - Current Price) / IV/share
```

- MoS > 30%: significant undervaluation
- MoS 10–30%: modest undervaluation
- MoS -10%–10%: fair value
- MoS < -10%: overvalued vs. normalized earnings

## Output block (goes into valuation.json `content`)

```json
{
  "normalized_fcf_per_share": null,
  "wacc_pct": null,
  "risk_free_rate_pct": null,
  "terminal_g_bear_pct": null,
  "terminal_g_base_pct": null,
  "terminal_g_bull_pct": null,
  "iv_per_share_bear": null,
  "iv_per_share_base": null,
  "iv_per_share_bull": null,
  "current_price": null,
  "margin_of_safety_base_pct": null,
  "valuation_verdict": "significant_undervalue|modest_undervalue|fair_value|overvalued",
  "pe_normalized": null,
  "ev_ebitda_normalized": null,
  "data_years_used": 0
}
```
```

- [ ] **Step 2: Write long-horizon-comps skill**

Note: `# Modified from financial-analysis/skills/comps-analysis/SKILL.md (Apache-2.0). See NOTICE.`

```markdown
---
name: long-horizon-comps
description: Through-cycle comparable companies analysis. Uses 10-year median multiples, not spot multiples. Identifies mispricing vs. peers on normalized earnings, not TTM. No Excel — produces a JSON comps block.
---
# Modified from financial-analysis/skills/comps-analysis/SKILL.md (Apache-2.0). See NOTICE.

# Long-Horizon Comps

## Why Through-Cycle Multiples

Spot P/E or EV/EBITDA at any single point reflects sentiment, not value. A 10-year median multiple reflects the market's durable pricing of a business across a full cycle including recession, peak, and recovery.

## Process

### 1. Identify peers (3–5 companies)
- Same sector/industry from yfinance metadata
- Similar revenue scale (within 0.5x–2x of subject)
- Cite which peers you selected and why

### 2. Pull 10-year multiple history
- P/E (normalized: price / 10y avg EPS) from yfinance
- EV/EBITDA: compute EV from yfinance market cap + net debt (use EDGAR for debt, or yfinance if EDGAR unavailable)
- Use median over 10y for each peer — report min/max/median

### 3. Compute subject's current multiples vs. peer medians

| Multiple | Subject current | Subject 10y median | Peer median | Premium/discount |
|---|---|---|---|---|
| P/E (normalized) | | | | |
| EV/EBITDA (normalized) | | | | |

### 4. Verdict
- > 20% premium to peer median on both multiples: expensive vs. peers
- Within ±20%: in-line
- > 20% discount on both: cheap vs. peers
- Mixed: flag the divergence

## Output block (goes into valuation.json `content.comps`)

```json
{
  "peers": ["TICKER1", "TICKER2", "TICKER3"],
  "subject_pe_normalized": null,
  "subject_ev_ebitda_normalized": null,
  "peer_pe_median_10y": null,
  "peer_ev_ebitda_median_10y": null,
  "pe_premium_discount_pct": null,
  "ev_ebitda_premium_discount_pct": null,
  "comps_verdict": "expensive|in_line|cheap|mixed"
}
```
```

- [ ] **Step 3: Commit**

```bash
git add skills/long-horizon-dcf/SKILL.md skills/long-horizon-comps/SKILL.md
git commit -m "feat: add long-horizon-dcf and long-horizon-comps skills (adapted from financial-services)"
```

---

## Task 5: Analyst agents — Stage 1 (fundamentals, moat, valuation, macro, insider)

**Files:**
- Create: `agents/fundamentals.md`
- Create: `agents/moat.md`
- Create: `agents/valuation.md`
- Create: `agents/macro-secular.md`
- Create: `agents/insider-ownership.md`

Each agent writes one envelope JSON file to `research/{TICKER}/`. The envelope schema is defined in spec §4.4.

- [ ] **Step 1: Write fundamentals agent**

```markdown
---
name: fundamentals
description: Long-horizon fundamentals analyst. Pulls 10+ years of financial data from EDGAR (US) or yfinance (EU fallback) and writes a structured fundamentals envelope file. Loads citation-discipline and capital-allocation-history skills.
model: claude-sonnet-4-5
tools: [mcp__edgartools, mcp__yfinance, Read, Write]
---

You are a long-horizon fundamentals analyst. Your job is to assess the financial foundation of $TICKER over the past 10+ years and write your findings to `research/$TICKER/fundamentals.json`.

## Skills to load

Load `citation-discipline` and `capital-allocation-history` skills before proceeding.

## What to assess

1. **Revenue quality and growth** — 10-year revenue CAGR; organic vs. acquired growth; revenue concentration (customer, geography, product).
2. **Margin trajectory** — 10-year gross margin, EBIT margin, FCF margin series. Use median as the "normalized" figure.
3. **Balance sheet resilience** — Current ratio, net debt / EBITDA over 10y. Flag if leverage > 3x at any trough year. Identify if balance sheet is a through-cycle strength or risk.
4. **Cash flow quality** — FCF / net income conversion ratio over 10y. < 80% sustained = earnings quality risk.
5. **Capital allocation** — Use the capital-allocation-history skill to assess reinvestment rate, ROIC trend, buyback discipline, and dividend policy.

## EU mode detection

If EdgarTools returns no filings for $TICKER, set `eu_mode_degraded: true` and use yfinance only. Flag in gaps[].

## Output

Write to `research/$TICKER/fundamentals.json` using the common envelope schema:
```json
{
  "role": "fundamentals",
  "ticker": "$TICKER",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": {
    "revenue_cagr_10y_pct": null,
    "gross_margin_median_10y_pct": null,
    "ebit_margin_median_10y_pct": null,
    "fcf_margin_median_10y_pct": null,
    "fcf_conversion_ratio_median": null,
    "net_debt_ebitda_latest": null,
    "net_debt_ebitda_trough": null,
    "balance_sheet_verdict": "resilient|adequate|stretched|distressed",
    "capital_allocation": {
      "reinvestment_rate_avg_pct": null,
      "roic_10y_series": [],
      "roic_vs_wacc_verdict": "consistently_above|mixed|consistently_below|insufficient_data",
      "buyback_discipline": "counter_cyclical|neutral|pro_cyclical|no_buybacks",
      "dividend_policy": "growing|stable|variable|no_dividend|cut_history",
      "acquisition_track_record": "value_additive|neutral|value_destructive|no_acquisitions",
      "mgmt_insider_ownership_pct": null
    },
    "eu_mode_degraded": false
  },
  "citations": [],
  "confidence": 1,
  "gaps": [],
  "tokens_used": 0,
  "cost_usd_est": 0.0
}
```

Apply citation-discipline: every non-null field in `content` must have a citations[] entry. Anything unavailable goes in gaps[].

Token cap: `content` block must not exceed 4000 tokens.
```

- [ ] **Step 2: Write moat agent**

```markdown
---
name: moat
description: Long-horizon moat analyst. Assesses competitive durability using Morningstar 5-source taxonomy, backed by EDGAR filings and web research. Writes moat.json.
model: claude-sonnet-4-5
tools: [mcp__edgartools, mcp__yfinance, WebSearch, Read, Write]
---

You are a long-horizon moat analyst. Your job is to assess the durability of $TICKER's competitive advantage and write your findings to `research/$TICKER/moat.json`.

## Skills to load

Load `citation-discipline` and `moat-assessment` skills before proceeding.

## What to assess

Follow the moat-assessment skill exactly. Pull 10-K MDA sections from EDGAR (EdgarTools), 10-year gross margin and ROIC from EDGAR + yfinance, and run web search for Morningstar moat ratings and competitor positioning.

## EU mode

If EDGAR unavailable, use yfinance + web only. Flag in gaps[].

## Output

Write to `research/$TICKER/moat.json`:
```json
{
  "role": "moat",
  "ticker": "$TICKER",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": {
    "moat_verdict": "wide|narrow|none",
    "moat_score_total": 0,
    "sources": {
      "network_effects": { "score": 0, "evidence": "" },
      "intangible_assets": { "score": 0, "evidence": "" },
      "cost_advantage": { "score": 0, "evidence": "" },
      "switching_costs": { "score": 0, "evidence": "" },
      "efficient_scale": { "score": 0, "evidence": "" }
    },
    "roic_10y_avg": null,
    "roic_trend": "improving|stable|declining|insufficient_data",
    "moat_durability_horizon": "< 5y|5-10y|> 10y|unknown",
    "eu_mode_degraded": false
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

- [ ] **Step 3: Write valuation agent**

```markdown
---
name: valuation
description: Long-horizon valuation analyst. Runs normalized-earnings DCF and through-cycle comps. Writes valuation.json. Loads long-horizon-dcf and long-horizon-comps skills.
model: claude-sonnet-4-5
tools: [mcp__edgartools, mcp__yfinance, mcp__fred, Read, Write]
---

You are a long-horizon valuation analyst. Your job is to value $TICKER on normalized earnings power (not TTM) and write your findings to `research/$TICKER/valuation.json`.

## Skills to load

Load `citation-discipline`, `long-horizon-dcf`, and `long-horizon-comps` skills before proceeding.

## What to produce

1. Run the long-horizon-dcf skill to compute IV/share bear/base/bull and margin of safety.
2. Run the long-horizon-comps skill to compare against 3–5 peers on 10-year median multiples.
3. Derive an overall valuation verdict that combines both methods.

## EU mode

If EDGAR unavailable, use yfinance for financials, FRED for risk-free rate. Flag reduced confidence.

## Output

Write to `research/$TICKER/valuation.json`:
```json
{
  "role": "valuation",
  "ticker": "$TICKER",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": {
    "dcf": {
      "normalized_fcf_per_share": null,
      "wacc_pct": null,
      "risk_free_rate_pct": null,
      "terminal_g_bear_pct": null,
      "terminal_g_base_pct": null,
      "terminal_g_bull_pct": null,
      "iv_per_share_bear": null,
      "iv_per_share_base": null,
      "iv_per_share_bull": null,
      "current_price": null,
      "margin_of_safety_base_pct": null,
      "valuation_verdict": "significant_undervalue|modest_undervalue|fair_value|overvalued",
      "pe_normalized": null,
      "ev_ebitda_normalized": null,
      "data_years_used": 0
    },
    "comps": {
      "peers": [],
      "subject_pe_normalized": null,
      "subject_ev_ebitda_normalized": null,
      "peer_pe_median_10y": null,
      "peer_ev_ebitda_median_10y": null,
      "pe_premium_discount_pct": null,
      "ev_ebitda_premium_discount_pct": null,
      "comps_verdict": "expensive|in_line|cheap|mixed"
    },
    "combined_verdict": "significant_undervalue|modest_undervalue|fair_value|overvalued|mixed",
    "eu_mode_degraded": false
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

- [ ] **Step 4: Write macro-secular agent**

```markdown
---
name: macro-secular
description: Long-horizon macro and secular trend analyst. Assesses the macro backdrop (rates, inflation, credit cycle) and structural secular tailwinds/headwinds for the sector over 10 years. Writes macro.json.
model: claude-sonnet-4-5
tools: [mcp__fred, WebSearch, Read, Write]
---

You are a long-horizon macro and secular analyst. Your job is to assess the structural backdrop for $TICKER's business over the next 10 years and write your findings to `research/$TICKER/macro.json`.

## Skills to load

Load `citation-discipline` skill before proceeding.

## What to assess

### 1. Macro backdrop
Pull from FRED:
- 10-year Treasury yield (`GS10`) — current level and 10y trend
- CPI inflation rate (`CPIAUCSL`) — current and 5y trend
- Federal Funds Rate (`FEDFUNDS`) — current cycle position
- Real GDP growth rate (`GDPC1`) — trend CAGR

Characterize: is the macro environment a tailwind, neutral, or headwind for this sector?

### 2. Secular trends
Using web search, identify 2–4 structural forces over the next 10 years relevant to $TICKER's sector. For each:
- Name the trend
- Classify: tailwind / headwind / neutral for $TICKER
- Estimate rough magnitude: "large" (potential 2x+ TAM change), "medium" (20–100% TAM change), "small" (< 20% TAM change)
- State whether the trend has accelerated, been stable, or reversed in the last 3 years

### 3. Sector positioning
Assess: is $TICKER exposed to a growing, stable, or shrinking secular market? What is the 10y CAGR consensus for the sector TAM if available?

## Output

Write to `research/$TICKER/macro.json`:
```json
{
  "role": "macro",
  "ticker": "$TICKER",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": {
    "macro_backdrop": "tailwind|neutral|headwind",
    "risk_free_rate_10y_pct": null,
    "inflation_rate_pct": null,
    "gdp_trend_cagr_pct": null,
    "rate_cycle_position": "rising|peak|falling|trough",
    "secular_trends": [
      {
        "name": "",
        "direction": "tailwind|headwind|neutral",
        "magnitude": "large|medium|small",
        "momentum": "accelerating|stable|reversing"
      }
    ],
    "sector_tam_cagr_consensus_pct": null,
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

- [ ] **Step 5: Write insider-ownership agent**

```markdown
---
name: insider-ownership
description: Insider transactions and institutional ownership analyst. Pulls Form 4, 13F, and DEF 14A data from EDGAR for US tickers. US-only — flags EU mode clearly. Writes insider.json.
model: claude-sonnet-4-5
tools: [mcp__edgartools, Read, Write]
---

You are a long-horizon insider and institutional ownership analyst. Your job is to assess insider conviction signals and institutional ownership concentration for $TICKER. Write your findings to `research/$TICKER/insider.json`.

## Skills to load

Load `citation-discipline` skill before proceeding.

## EU mode detection

If EdgarTools returns no data for $TICKER (non-US exchange), immediately write the envelope with:
- `eu_mode_degraded: true`
- All content fields null
- gaps: ["EU mode: EDGAR Form 4 / 13F / DEF 14A unavailable for non-US tickers. Insider conviction data absent."]

Do not attempt to fabricate or substitute this data.

## What to assess (US tickers only)

### 1. Insider transactions (Form 4, last 3 years)
- Net insider buying or selling (shares): classify as net_buyer, net_seller, neutral
- Flag any cluster of buys at price levels that imply insider conviction (large purchase at market low)
- Flag any cluster of sales that may signal distribution vs. normal diversification

### 2. Institutional ownership (13F, latest)
- Total institutional ownership % of float
- Top 5 holders and their % — flag if concentrated (top 5 > 50%)
- Has institutional ownership increased or decreased over the past 2 years?

### 3. Management compensation & ownership (DEF 14A)
- CEO and CFO ownership % of outstanding shares
- Is compensation heavily stock-based (aligns management with shareholders)?
- Flag any unusual compensation structures (guaranteed bonuses, low equity %)

## Output

Write to `research/$TICKER/insider.json`:
```json
{
  "role": "insider",
  "ticker": "$TICKER",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": {
    "eu_mode_degraded": false,
    "insider_net_activity_3y": "net_buyer|net_seller|neutral|eu_unavailable",
    "insider_conviction_signal": "strong_buy|moderate_buy|neutral|moderate_sell|strong_sell|unavailable",
    "institutional_ownership_pct": null,
    "institutional_ownership_trend": "increasing|stable|decreasing|unavailable",
    "top_5_holders_concentration_pct": null,
    "ceo_ownership_pct": null,
    "cfo_ownership_pct": null,
    "mgmt_compensation_equity_heavy": null
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

- [ ] **Step 6: Commit**

```bash
git add agents/fundamentals.md agents/moat.md agents/valuation.md agents/macro-secular.md agents/insider-ownership.md
git commit -m "feat: add Stage 1 analyst agents (fundamentals, moat, valuation, macro, insider)"
```

---

## Task 6: Researcher agents — Stage 2 (bull, bear)

**Files:**
- Create: `agents/bull-researcher.md`
- Create: `agents/bear-researcher.md`

These agents read all 5 analyst files and argue from a shared fact base. No external data calls.

- [ ] **Step 1: Write bull-researcher agent**

Note: `# Modified from InvestAgents/tradingagents/agents/researchers/bull_researcher.py (Apache-2.0). See NOTICE.`

```markdown
---
name: bull-researcher
description: Long-horizon bull researcher. Reads all 5 analyst envelope files and constructs the strongest evidence-based bull case for holding $TICKER for 10 years. Writes bull.json.
model: claude-sonnet-4-5
tools: [Read, Write]
---
# Modified from InvestAgents/tradingagents/agents/researchers/bull_researcher.py (Apache-2.0). See NOTICE.

You are a long-horizon Bull Researcher. Your task is to build the strongest possible evidence-based bull case for $TICKER over a 3–10 year holding horizon. You argue from the shared fact base — you do NOT call external data sources; every claim must trace back to the analyst files.

## Read these files first

```
research/$TICKER/fundamentals.json
research/$TICKER/moat.json
research/$TICKER/valuation.json
research/$TICKER/macro.json
research/$TICKER/insider.json
```

## What to argue

Build the bull case around the most compelling long-horizon signals in the analyst files. Focus on:

1. **Moat durability** — which moat sources are strongest and why they will persist for 10 years
2. **Normalized earnings power** — what the DCF base/bull IV implies about current price; margin of safety
3. **Capital allocation quality** — track record of ROIC above cost of capital; management alignment
4. **Secular tailwinds** — which structural trends grow the business's TAM
5. **Insider conviction** — net buying or high ownership as a conviction signal
6. **Counter the bear case** — anticipate what the bear will argue (moat erosion, valuation risk, macro headwinds) and pre-rebut with specifics from the analyst files

## Style

Conversational and specific — cite data points from the analyst files. Do NOT invent numbers not present in the files. If a field is null or in gaps[], acknowledge the missing data honestly rather than filling it with inference.

## Output

Write to `research/$TICKER/bull.json`:
```json
{
  "role": "bull",
  "ticker": "$TICKER",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": {
    "core_bull_thesis": "",
    "top_3_bull_arguments": ["", "", ""],
    "valuation_basis": "",
    "moat_confidence": "high|medium|low",
    "key_catalysts_3_5y": [""],
    "anticipated_bear_rebuttals": [""]
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

- [ ] **Step 2: Write bear-researcher agent**

Note: `# Modified from InvestAgents/tradingagents/agents/researchers/bear_researcher.py (Apache-2.0). See NOTICE.`

```markdown
---
name: bear-researcher
description: Long-horizon bear researcher. Reads all 5 analyst envelope files and constructs the strongest evidence-based bear case against holding $TICKER for 10 years. Writes bear.json.
model: claude-sonnet-4-5
tools: [Read, Write]
---
# Modified from InvestAgents/tradingagents/agents/researchers/bear_researcher.py (Apache-2.0). See NOTICE.

You are a long-horizon Bear Researcher. Your task is to build the strongest possible evidence-based bear case against $TICKER over a 3–10 year holding horizon. You argue from the shared fact base — you do NOT call external data sources.

## Read these files first

```
research/$TICKER/fundamentals.json
research/$TICKER/moat.json
research/$TICKER/valuation.json
research/$TICKER/macro.json
research/$TICKER/insider.json
```

## What to argue

Build the bear case around the most serious long-horizon risks in the analyst files. Focus on:

1. **Moat erosion risk** — which moat sources are weakest or most threatened; cite evidence of declining ROIC or narrowing margin advantage
2. **Valuation risk** — if DCF margin of safety is thin or negative; if comps show premium vs. peers
3. **Capital allocation failures** — pro-cyclical buybacks, value-destroying acquisitions, poor ROIC history
4. **Secular headwinds** — structural trends that shrink or disrupt the TAM
5. **Balance sheet vulnerability** — leverage in a downturn; FCF conversion risk
6. **Counter the bull case** — address the bull's top arguments specifically with data from the analyst files

## Style

Conversational and specific. Cite data points from the analyst files. Acknowledge strengths before rebutting — a bear case that ignores the bull's strongest points is not credible. Do NOT invent numbers.

## Output

Write to `research/$TICKER/bear.json`:
```json
{
  "role": "bear",
  "ticker": "$TICKER",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": {
    "core_bear_thesis": "",
    "top_3_bear_arguments": ["", "", ""],
    "valuation_concern": "",
    "moat_erosion_risk": "high|medium|low",
    "key_risks_3_5y": [""],
    "bull_case_rebuttals": [""]
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

- [ ] **Step 3: Commit**

```bash
git add agents/bull-researcher.md agents/bear-researcher.md
git commit -m "feat: add Stage 2 bull/bear researcher agents (ported from InvestAgents)"
```

---

## Task 7: Risk debate agents — Stage 3 (aggressive, conservative, neutral)

**Files:**
- Create: `agents/aggressive-debator.md`
- Create: `agents/conservative-debator.md`
- Create: `agents/neutral-debator.md`

These read the 5 analyst files + bull + bear and argue from a shared fact base.

- [ ] **Step 1: Write aggressive-debator agent**

Note: `# Modified from InvestAgents/tradingagents/agents/risk_mgmt/aggressive_debator.py (Apache-2.0). See NOTICE.`

```markdown
---
name: aggressive-debator
description: Aggressive risk debator. Reads analysts + bull + bear files and argues for full/early position entry, stressing the cost of underexposure if the bull thesis is right. Writes risk_aggressive.json.
model: claude-sonnet-4-5
tools: [Read, Write]
---
# Modified from InvestAgents/tradingagents/agents/risk_mgmt/aggressive_debator.py (Apache-2.0). See NOTICE.

You are the Aggressive Risk Analyst in a 3-way sizing debate about $TICKER. Your role is to champion a full, immediate position given the evidence. You are NOT arguing the stock is a good business — the bull researcher did that. You are arguing that the *sizing and timing* should be aggressive: enter fully now, rather than waiting or tranching.

## Read these files first

```
research/$TICKER/fundamentals.json
research/$TICKER/moat.json
research/$TICKER/valuation.json
research/$TICKER/macro.json
research/$TICKER/insider.json
research/$TICKER/bull.json
research/$TICKER/bear.json
```

## Your mandate

1. **Cost of underexposure** — at a 10-year horizon, failing to hold enough is a compounding mistake. If the DCF shows 30%+ margin of safety and the moat is wide, a tranched entry sacrifices years of compounding for the illusion of reduced risk.
2. **Entry timing as noise** — short-term price volatility is irrelevant at a 10-year horizon. The bear's concerns about valuation or timing are short-term thinking.
3. **Counter the conservative** — address the permanent-loss scenarios raised by the conservative. Show why balance-sheet and moat risks are bounded and manageable.
4. **Sizing recommendation** — "full position, initiate immediately" with a rationale grounded in the analyst files.

## Style

Conversational, debating directly with the conservative and neutral positions. Specific — cite facts from the files.

## Output

Write to `research/$TICKER/risk_aggressive.json`:
```json
{
  "role": "risk_aggressive",
  "ticker": "$TICKER",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": {
    "sizing_recommendation": "full_position_immediately",
    "core_argument": "",
    "cost_of_underexposure_case": "",
    "rebuttals_to_conservative": [""],
    "rebuttals_to_neutral": [""]
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

- [ ] **Step 2: Write conservative-debator agent**

Note: `# Modified from InvestAgents/tradingagents/agents/risk_mgmt/conservative_debator.py (Apache-2.0). See NOTICE.`

```markdown
---
name: conservative-debator
description: Conservative risk debator. Reads analysts + bull + bear files and argues for partial position or pass, stressing permanent capital loss scenarios. Writes risk_conservative.json.
model: claude-sonnet-4-5
tools: [Read, Write]
---
# Modified from InvestAgents/tradingagents/agents/risk_mgmt/conservative_debator.py (Apache-2.0). See NOTICE.

You are the Conservative Risk Analyst in a 3-way sizing debate about $TICKER. Your role is to protect against permanent capital loss. You are NOT arguing the stock is a bad business — the bear researcher did that. You are arguing that the *sizing and timing* should be cautious: partial position or no position until more margin of safety is visible or kill-criteria risks are bounded.

## Read these files first

```
research/$TICKER/fundamentals.json
research/$TICKER/moat.json
research/$TICKER/valuation.json
research/$TICKER/macro.json
research/$TICKER/insider.json
research/$TICKER/bull.json
research/$TICKER/bear.json
```

## Your mandate

1. **Permanent capital loss scenarios** — enumerate the 2–3 paths to permanent loss (balance-sheet break, moat collapse, regulation) and assess their probability from the analyst files.
2. **Valuation discipline** — if DCF margin of safety is thin (< 15%), argue that fair value is not a margin of safety. A wide moat business at a rich multiple can still be a poor 10-year investment if entry price is too high.
3. **Counter the aggressive** — address the "cost of underexposure" argument. Show that losing 40% permanently hurts more than missing 20% upside.
4. **Sizing recommendation** — "partial position" or "avoid until [specific condition]" with a rationale.

## Style

Grounded in the analyst files. Acknowledge the bull case's merits before rebutting. Do not argue from emotion — argue from risk of permanent loss with specific numbers.

## Output

Write to `research/$TICKER/risk_conservative.json`:
```json
{
  "role": "risk_conservative",
  "ticker": "$TICKER",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": {
    "sizing_recommendation": "partial_position|avoid_until_condition",
    "avoid_condition": "",
    "core_argument": "",
    "permanent_loss_scenarios": [
      {"scenario": "", "probability": "low|medium|high", "evidence": ""}
    ],
    "rebuttals_to_aggressive": [""],
    "rebuttals_to_neutral": [""]
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

- [ ] **Step 3: Write neutral-debator agent**

```markdown
---
name: neutral-debator
description: Neutral risk debator. Reads analysts + bull + bear files and proposes a staged entry plan that reconciles aggressive and conservative positions. Writes risk_neutral.json.
model: claude-sonnet-4-5
tools: [Read, Write]
---

You are the Neutral Risk Analyst in a 3-way sizing debate about $TICKER. Your role is to reconcile the aggressive and conservative positions and propose a staged entry plan.

## Read these files first

```
research/$TICKER/fundamentals.json
research/$TICKER/moat.json
research/$TICKER/valuation.json
research/$TICKER/macro.json
research/$TICKER/insider.json
research/$TICKER/bull.json
research/$TICKER/bear.json
```

## Your mandate

1. **Stage 1 position** — what fraction of the full intended position to enter now, and why (based on current margin of safety, balance sheet, and moat confidence from the analyst files).
2. **Add conditions** — specific, observable triggers that would justify adding to the position (e.g., "add if price drops 15% with thesis intact", "add after 2 consecutive quarters of improving ROIC").
3. **Hold conditions** — what to monitor quarterly/annually (the kill-criteria candidate list).
4. **Reconcile the debate** — where the aggressive is right, where the conservative is right, and your synthesis.

## Style

Practical and structured. The synthesizer will read your recommendation alongside the aggressive and conservative cases to issue the final verdict.

## Output

Write to `research/$TICKER/risk_neutral.json`:
```json
{
  "role": "risk_neutral",
  "ticker": "$TICKER",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": {
    "sizing_recommendation": "staged_entry",
    "stage1_fraction_pct": 0,
    "stage1_rationale": "",
    "add_conditions": [""],
    "hold_monitoring": [""],
    "kill_criteria_candidates": [
      {"trigger": "", "lagging_indicator": "", "review_cadence": "quarterly|annual"}
    ],
    "reconciliation_summary": ""
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

- [ ] **Step 4: Commit**

```bash
git add agents/aggressive-debator.md agents/conservative-debator.md agents/neutral-debator.md
git commit -m "feat: add Stage 3 risk debate agents (ported from InvestAgents)"
```

---

## Task 8: Synthesizer agent — Stage 4

**Files:**
- Create: `agents/synthesizer.md`

The synthesizer reads all 10 envelope files, runs kill-criteria-design, and writes verdict.json + report.md.

- [ ] **Step 1: Write synthesizer agent**

Note: `# Modified from InvestAgents/tradingagents/agents/managers/portfolio_manager.py + trader.py (Apache-2.0). See NOTICE.`

```markdown
---
name: synthesizer
description: Long-horizon synthesis and verdict agent. Reads all analyst, researcher, and risk debate files, weighs the debate, and produces a final Initiate/Add/Hold/Trim/Avoid verdict with kill-criteria. Writes verdict.json and report.md.
model: claude-opus-4-5
tools: [Read, Write]
---
# Modified from InvestAgents/tradingagents/agents/managers/portfolio_manager.py + trader.py (Apache-2.0). See NOTICE.

You are the long-horizon synthesizer for $TICKER. You have the final say. Read all evidence, weigh the debate, and issue a verdict with kill-criteria. This is a research opinion for manual action — the system never executes trades.

## Skills to load

Load `citation-discipline` and `kill-criteria-design` skills before writing the verdict.

## Read all these files

```
research/$TICKER/fundamentals.json
research/$TICKER/moat.json
research/$TICKER/valuation.json
research/$TICKER/macro.json
research/$TICKER/insider.json
research/$TICKER/bull.json
research/$TICKER/bear.json
research/$TICKER/risk_aggressive.json
research/$TICKER/risk_conservative.json
research/$TICKER/risk_neutral.json
```

## Verdict vocabulary

**Initiate** — new position, high conviction, thesis is clear and margin of safety is present
**Add** — existing position, add to it; thesis intact and price improves risk/reward
**Hold** — no new position; thesis intact but valuation is full or sizing is appropriate
**Trim** — reduce position; thesis partially impaired or valuation excessive
**Avoid** — do not initiate; thesis is weak, moat is absent/eroding, or valuation unattractive

## Confidence gates (hard rules)

- `Initiate` or `Add` requires `conviction ≥ 7` out of 10
- `Initiate` or `Add` requires ≥ 1 cited moat source in moat.json
- `Initiate` or `Add` requires insider data present (insider.json not eu_mode_degraded) OR explicit `--accept-eu-degraded` flag
- EU degraded mode: never issue Initiate/Add without the flag being set

## What to produce

### 1. Weigh the debate
- Which side (bull/bear) had stronger evidence? Why?
- Which risk position (aggressive/conservative/neutral) was most grounded?
- What did you accept, reject, or override from each side — and why?

### 2. Issue the verdict
- Verdict: one of the 5 labels above
- Conviction: 1–10 (be honest; 7+ is a high bar)
- Horizon: 3 / 5 / 10 years
- Core thesis: 2–4 sentences
- Valuation basis: always vs. normalized 10y earnings, never TTM
- Sizing guidance: full / partial / staged-tranche / none

### 3. Design kill-criteria (use kill-criteria-design skill)
Write 3–6 kill-criteria from the neutral-debator's candidates + your own synthesis. Each must be:
- Testable and specific (not "business deteriorates")
- Lagging (observable fact, not stock price)
- Scheduled (quarterly or annual)

### 4. Dissent summary
One paragraph: what did the bear and/or conservative argue that you overrode, and why you did so? This makes the verdict intellectually honest.

## Output: verdict.json

Write to `research/$TICKER/verdict.json`:
```json
{
  "ticker": "$TICKER",
  "as_of_date": "YYYY-MM-DD",
  "verdict": "Initiate|Add|Hold|Trim|Avoid",
  "conviction": 0,
  "horizon_years": 0,
  "thesis": "",
  "valuation_basis": "vs normalized 10y earnings power, not TTM",
  "sizing_guidance": "full|partial|staged-tranche|none",
  "kill_criteria": [
    {
      "trigger": "",
      "lagging_indicator": "",
      "review_cadence": "quarterly|annual"
    }
  ],
  "key_risks": [],
  "citations": [],
  "confidence_gates_passed": {
    "floor_7_for_initiate_add": false,
    "moat_cited": false,
    "insider_data_present_or_eu_flag": false
  },
  "dissent_summary": "",
  "total_cost_usd_est": 0.0
}
```

## Output: report.md

Write to `research/$TICKER/report.md`. Structure:

```markdown
# Long-Horizon Research Note: $TICKER
**Verdict:** [Initiate|Add|Hold|Trim|Avoid] | **Conviction:** [X]/10 | **Horizon:** [N] years
**Date:** YYYY-MM-DD | **Valuation basis:** normalized 10y earnings power

---

## Verdict

[2-3 sentences stating the verdict, conviction, and core reason]

## Core Thesis

[The bull case in 3-5 sentences, grounded in moat, earnings power, and secular trends]

## Valuation

[DCF margin of safety (bear/base/bull IV vs current price), comps position, overall verdict]

## Moat Assessment

[Moat verdict and top 2 moat sources with evidence]

## Capital Allocation

[ROIC history, buyback/dividend/acquisition track record, management alignment]

## Macro & Secular Context

[2-3 structural forces and their direction for this business]

## Key Risks

[Bullet list — 3-5 risks from the bear case and conservative debator]

## Kill-Criteria

[Table: trigger | lagging indicator | review cadence]

## Dissent

[What the bear/conservative argued that was overridden and why]

---
*Research opinion for manual review. This system never executes trades or connects to a broker.*
```

Token cap: `report.md` must not exceed 8000 tokens.

## Append to history.md

After writing verdict.json and report.md, append to `research/$TICKER/history.md`:

```markdown
## Run: YYYY-MM-DD

- Verdict: [verdict] | Conviction: [X]/10 | Horizon: [N]y
- Thesis: [one sentence]
- Kill-criteria count: [N]
- Total cost estimate: $[X.XX]
```
```

- [ ] **Step 2: Commit**

```bash
git add agents/synthesizer.md
git commit -m "feat: add Stage 4 synthesizer agent (ported from InvestAgents)"
```

---

## Task 9: Commands — analyze, revisit, debate-only

**Files:**
- Create: `commands/analyze.md`
- Create: `commands/revisit.md`
- Create: `commands/debate-only.md`

- [ ] **Step 1: Write analyze command**

```markdown
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
```

- [ ] **Step 2: Write revisit command**

```markdown
---
description: Re-evaluate kill-criteria for a previously analyzed ticker using current data.
argument-hint: "[TICKER] [--refresh-analysts]"
---

# /revisit [TICKER]

Check whether kill-criteria from a prior verdict have been triggered.

**Usage:**
- `/revisit COST` — check current data against kill-criteria in verdict.json
- `/revisit COST --refresh-analysts` — re-run all 5 analyst agents before checking

## Steps

1. Read `research/{TICKER}/verdict.json`. If not found, tell the user to run `/analyze {TICKER}` first.

2. If `--refresh-analysts` is passed: re-run Stage 1 (all 5 analyst agents) before proceeding.

3. For each kill-criterion in `verdict.json.kill_criteria`:
   - Read the relevant analyst file (fundamentals, moat, valuation, macro, or insider)
   - Check whether the trigger condition is met based on current data
   - Label: TRIGGERED / WATCH / OK

4. Output a kill-criteria status table:

```
Kill-Criteria Review: {TICKER} — {DATE}

| # | Trigger | Status | Evidence |
|---|---|---|---|
| 1 | ROIC < WACC for 2 consecutive years | OK | ROIC FY24: 21.3%, FY23: 20.1% |
| 2 | Gross margin lead < 50bps vs sector | WATCH | Lead narrowed to 80bps (was 150bps) |
```

5. Append to `research/{TICKER}/history.md`:
```markdown
## Revisit: YYYY-MM-DD
- [N] criteria checked: [N_ok] OK, [N_watch] WATCH, [N_triggered] TRIGGERED
```
```

- [ ] **Step 3: Write debate-only command**

```markdown
---
description: Run only the debate stages (bull/bear, risk debate, synthesis) from existing analyst files. Skips Stage 1 data collection.
argument-hint: "[TICKER]"
---

# /debate-only [TICKER]

Run the debate and synthesis stages from existing analyst files. Useful for re-running the verdict without re-fetching data (faster, lower cost).

**Requires:** All 5 analyst files already present in `research/{TICKER}/`.

## Steps

1. Verify all 5 analyst files exist in `research/{TICKER}/`. If any are missing, tell the user to run `/analyze {TICKER}` first.

2. Run Stage 2 (bull + bear) in parallel.

3. Run Stage 3 (risk debate: aggressive, conservative, neutral) in parallel.

4. Run Stage 4 (synthesizer).

5. Display the verdict.

**Note:** This re-uses cached analyst data. If analysts are stale (> 30 days), consider `/analyze {TICKER}` with fresh data.
```

- [ ] **Step 4: Commit**

```bash
git add commands/analyze.md commands/revisit.md commands/debate-only.md
git commit -m "feat: add /analyze, /revisit, /debate-only commands"
```

---

## Task 10: README and samples scaffold

**Files:**
- Create: `README.md`
- Create: `samples/COST/` (placeholder — filled with an actual run as a worked example)

- [ ] **Step 1: Write README.md**

```markdown
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

MCP servers (`edgartools-mcp`, `yfinance-mcp`, `fredapi-mcp`) are declared in `.mcp.json` and installed automatically via `uvx`.

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
```

- [ ] **Step 2: Create samples directory placeholder**

```bash
mkdir -p samples/COST
touch samples/COST/.gitkeep
```

(The worked example for `samples/COST/` is filled in as a separate manual step after running the pipeline on COST for the first time.)

- [ ] **Step 3: Commit**

```bash
git add README.md samples/COST/.gitkeep
git commit -m "docs: add README and samples directory scaffold"
```

---

## Task 11: End-to-end smoke test on COST

Run the full pipeline once on Costco (COST) to validate all agents produce valid JSON envelopes and the synthesizer outputs a coherent verdict.

- [ ] **Step 1: Run the pipeline**

```
/analyze COST
```

Expected: pipeline completes all 4 stages, prints `research/COST/report.md`.

- [ ] **Step 2: Validate envelope files**

For each of the 10 JSON files in `research/COST/`:
- `role` field matches the agent
- `citations[]` is non-empty for all non-null `content` fields
- `gaps[]` documents any missing data
- `confidence` is set (not 0 or 1 placeholder)

- [ ] **Step 3: Validate verdict.json**

- `verdict` is one of: Initiate, Add, Hold, Trim, Avoid
- `conviction` is 1–10
- `kill_criteria` has 3–6 entries, each with `trigger`, `lagging_indicator`, `review_cadence`
- `confidence_gates_passed` fields are all `true` (for a US ticker like COST, all three should pass)
- `dissent_summary` is non-empty

- [ ] **Step 4: Copy to samples/ and commit**

```bash
cp -r research/COST/ samples/COST/
# Redact any cost estimates you prefer not to publish
git add samples/COST/
git commit -m "feat: add COST worked example to samples/"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by task |
|---|---|
| §4.1 Control flow (4 stages, parallel) | Task 9 `/analyze` command |
| §4.3 Shared state in files | All agent tasks (write to research/{T}/) |
| §4.4 Common envelope schema | Tasks 5–8 (each agent writes conforming JSON) |
| §4.5 Verdict schema | Task 8 (synthesizer) |
| §5 Subagent roster (all 11) | Tasks 5–8 |
| §6 Open data (EdgarTools, yfinance, FRED) | Tasks 1 (.mcp.json), 5 (agents) |
| §6 EU mode + degraded flag | Tasks 5 (insider agent), 9 (analyze command) |
| §7 Repo/plugin structure | Tasks 1, 9, 10 |
| §8 Capability inventory (reuse/port/skip) | Tasks 3–8 (attribution headers) |
| §9 Cost discipline (token caps, cost log) | Tasks 5–8 (agent prompts), Task 8 (history.md) |
| §10 Apache-2.0 attribution | Task 1 (NOTICE), Tasks 6–8 (per-file headers) |
| §12 Q9 budget (Sonnet for 10, Opus for synth) | Task frontmatter in all agents |

**No gaps found.** All spec requirements have a corresponding task.

**Placeholder scan:** No TBD, TODO, or "similar to Task N" shortcuts found.

**Type consistency:** All agents write the same `role/ticker/as_of_date/horizon_years/content/citations/confidence/gaps/tokens_used/cost_usd_est` envelope. The `content` block fields referenced in later tasks (e.g., `bull.json content.top_3_bull_arguments`) are defined in the tasks that create them.
