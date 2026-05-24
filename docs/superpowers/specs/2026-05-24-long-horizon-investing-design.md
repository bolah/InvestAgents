# Long-Horizon Investing Plugin — Design Spec

**Date:** 2026-05-24
**Status:** Approved (brainstorming complete, awaiting implementation plan)
**Author:** brainstormed with Claude Code

## 1. Goal

A Claude-Code-runnable plugin that analyzes a single equity ticker for **medium-to-long-term investment** (3 / 5 / 10-year horizons). A root command dispatches subagents in parallel, runs a bull/bear debate and a 3-way risk debate over a shared file-based fact base, and produces a reviewable research note ending in a verdict from a fixed vocabulary: **Initiate / Add / Hold / Trim / Avoid**.

The verdict is a **research opinion for manual action**. The system never executes trades, connects to a broker, or acts on the verdict.

## 2. Non-goals

- Short-term / earnings-week trading signals.
- Order execution, broker integration, portfolio accounting.
- Multi-ticker portfolio optimization (single-ticker per run).
- xlsx model authoring (deferred — out of scope for v1).
- IB / PE / wealth / KYC / GL / month-end workflows from the financial-services repo.

## 3. Objections to the spec (addressed up front)

1. **Is an LLM-issued verdict on a 10-year horizon meaningful?** Honestly, the load-bearing output is the **structured thesis + kill-criteria**, with the verdict label as a thin wrapper. The plugin treats it that way: the verdict gates on confidence ≥ 7/10, requires cited moat sources and insider/ownership data, and surfaces dissent from the bear and conservative debators in the final note.
2. **Does open data support long-horizon judgments?** US: yes (EDGAR gives 20+ years of filings + insider/13F). EU: no — yfinance-only, no free filings, no insider data. v1 ships **US-first with EU degraded mode** that is loudly flagged in the verdict file.
3. **Where does long-horizon reorientation fight the source repos?** Financial-services skills assume quarterly cadence (earnings-analysis, model-update, morning-note, catalyst-calendar) — these are skipped or reframed. InvestAgents leans on TTM and short-window news — its prompts are ported with explicit normalization to 10y averages and through-cycle multiples.
4. **Is per-ticker parallel fan-out worth its token cost?** At ~11 LLM calls per ticker (5 analysts + 2 researchers + 3 risk + 1 synthesizer) on Sonnet+Opus mix, each run is well under $10 per ticker. The weakest assumption is that more analysts produce better verdicts — they may produce *more confident* verdicts without being more *correct*. The kill-criteria + confidence gate are the safeguards.

## 4. Architecture

### 4.1 Control flow

```
/analyze TICKER
  └─► Stage 1 — Analysts (parallel, 5 subagents)
        ├─ fundamentals
        ├─ moat
        ├─ valuation
        ├─ macro-secular
        └─ insider-ownership
  └─► Stage 2 — Researchers (parallel, 2 subagents; read all 5 analyst files)
        ├─ bull-researcher
        └─ bear-researcher
  └─► Stage 3 — Risk debate (parallel, 3 subagents; read analysts + bull + bear)
        ├─ aggressive-debator
        ├─ conservative-debator
        └─ neutral-debator
  └─► Stage 4 — Synthesizer (sequential, 1 subagent; reads everything)
        └─ writes verdict.json + report.md
```

### 4.2 Why a 3-way risk debate at long horizon

Bull/bear argues *what is true about the business and price*. Risk debate argues *how to size and stage exposure given those truths*.

- **Aggressive** — pushes for full position now; stress-tests the cost of underexposure if the thesis is right.
- **Conservative** — pushes for partial position or pass; stress-tests permanent capital loss (balance-sheet break, moat erosion).
- **Neutral** — proposes tranched entry against kill-criteria milestones; reconciles the two.

The synthesizer issues the verdict + sizing guidance + kill-criteria after reading all of it.

### 4.3 Shared state in files (not conversation)

All subagent I/O is via `research/{TICKER}/` files. Conversation carries control; files carry data. This is the audit trail.

```
research/
└── {TICKER}/
    ├── fundamentals.json
    ├── moat.json
    ├── valuation.json
    ├── macro.json
    ├── insider.json
    ├── bull.json
    ├── bear.json
    ├── risk_aggressive.json
    ├── risk_conservative.json
    ├── risk_neutral.json
    ├── verdict.json
    ├── report.md
    └── history.md           # append-only log across runs
```

`research/` is **gitignored by default**. A single committed worked example lives in `samples/{TICKER}/`.

### 4.4 Common envelope schema

Every analyst/researcher/debator file shares this envelope, with role-specific `content`:

```json
{
  "role": "fundamentals|moat|valuation|macro|insider|bull|bear|risk_*|synthesis",
  "ticker": "...",
  "as_of_date": "YYYY-MM-DD",
  "horizon_years": 10,
  "content": { /* role-specific fields */ },
  "citations": [
    {"claim": "...", "source": "edgar|yfinance|fred|web|tool", "url_or_id": "...", "retrieved_at": "..."}
  ],
  "confidence": 1-10,
  "gaps": ["data not available: ...", "EU mode: insider data unavailable"],
  "tokens_used": 0,
  "cost_usd_est": 0.0
}
```

**Citation discipline**: every numeric claim in `content` must map to a `citations[]` entry. If data is missing, write to `gaps[]` — never fabricate.

### 4.5 Verdict schema

```json
{
  "ticker": "...",
  "as_of_date": "YYYY-MM-DD",
  "verdict": "Initiate|Add|Hold|Trim|Avoid",
  "conviction": 1-10,
  "horizon_years": 3|5|10,
  "thesis": "...",
  "valuation_basis": "vs normalized 10y earnings power, not TTM",
  "sizing_guidance": "full|partial|staged-tranche|none",
  "kill_criteria": [
    {"trigger": "...", "lagging_indicator": "...", "review_cadence": "quarterly|annual"}
  ],
  "key_risks": ["..."],
  "citations": [...],
  "confidence_gates_passed": {
    "floor_7_for_initiate_add": true,
    "moat_cited": true,
    "insider_data_present_or_eu_flag": true
  },
  "dissent_summary": "what the bear/conservative said that synthesizer overrode and why",
  "total_cost_usd_est": 0.0
}
```

**Gate**: `verdict ∈ {Initiate, Add}` requires `conviction ≥ 7` AND ≥1 cited moat source AND (insider data present OR EU-mode flag).

## 5. Subagent roster

Each subagent is bound to specific data sources and produces one envelope file.

| Subagent | Reads | Writes | Primary data |
|---|---|---|---|
| fundamentals | EDGAR filings (10-K, 10-Q) via EdgarTools MCP | fundamentals.json | EDGAR (US) / yfinance (EU fallback) |
| moat | EDGAR + web | moat.json | EDGAR + web search (Morningstar 5-source taxonomy) |
| valuation | EDGAR + yfinance + FRED | valuation.json | EDGAR for normalized earnings, yfinance for price/multiples, FRED for risk-free rate |
| macro-secular | FRED + web | macro.json | FRED + web for secular trends |
| insider-ownership | EDGAR (Form 4, 13F, DEF 14A) | insider.json | EDGAR only — flagged unavailable in EU mode |
| bull-researcher | all 5 analyst files | bull.json | (no external data — argues from shared facts) |
| bear-researcher | all 5 analyst files | bear.json | (no external data — argues from shared facts) |
| aggressive-debator | analysts + bull + bear | risk_aggressive.json | (no external data) |
| conservative-debator | analysts + bull + bear | risk_conservative.json | (no external data) |
| neutral-debator | analysts + bull + bear | risk_neutral.json | (no external data) |
| synthesizer | everything | verdict.json + report.md | (no external data) |

**Symmetric data access**: bull and bear must read the *same* analyst files. The 3 risk debators must read the *same* superset. Asymmetry would bias the debate.

## 6. Open data set

### v1 (wire in now)

| Source | Use | Auth | Notes |
|---|---|---|---|
| **EdgarTools MCP** | US filings, Form 4 (insider), 13F (institutional), DEF 14A (compensation/governance) | none | Backbone for US fundamentals, moat evidence, capital allocation |
| **yfinance** | Price, dividend, buyback history (US + EU); basic financials (degraded for EU) | none | Long history; thin EU fundamentals |
| **FRED** | Macro: rates, inflation, yield curve, GDP | API key (free) | Risk-free rate for DCF; secular macro context |
| **Web search** | News, sentiment, secular-trend research, moat qualitative | varies | Citation-required; no fabricated quotes |

### Defer to v2

| Source | Why deferred |
|---|---|
| ECB / Eurostat | EU macro — needed once EU mode is upgraded from "degraded" to "first-class" |
| World Bank / IMF | Country/sector context for emerging-market analysis |
| OpenBB | Aggregator overlap with above; evaluate once v1 is real |

### EU gap flags

For EU tickers, the `insider.json` and EDGAR-backed portions of `fundamentals.json` and `moat.json` get an `eu_mode_degraded: true` flag and explicit `gaps[]` entries. The verdict gate refuses **Initiate/Add** for EU tickers in v1 unless the user passes `--accept-eu-degraded`.

## 7. Repo / plugin structure

Mirrors `financial-services/plugins/vertical-plugins/*/` so installation works the same way.

```
long-horizon-investing/                       # new plugin (top-level repo)
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── analyze.md                # /analyze TICKER → full pipeline
│   ├── revisit.md                # /revisit TICKER → re-check kill-criteria for prior verdict
│   └── debate-only.md            # /debate-only TICKER → skip analysts, debate from existing files
├── agents/
│   ├── fundamentals.md
│   ├── moat.md
│   ├── valuation.md
│   ├── macro-secular.md
│   ├── insider-ownership.md
│   ├── bull-researcher.md
│   ├── bear-researcher.md
│   ├── aggressive-debator.md     # ported from InvestAgents
│   ├── conservative-debator.md   # ported from InvestAgents
│   ├── neutral-debator.md        # ported from InvestAgents
│   └── synthesizer.md
├── skills/
│   ├── long-horizon-dcf/SKILL.md             # adapted from financial-analysis/dcf-model
│   ├── long-horizon-comps/SKILL.md           # adapted from financial-analysis/comps-analysis
│   ├── moat-assessment/SKILL.md              # new (Morningstar 5-source taxonomy)
│   ├── capital-allocation-history/SKILL.md   # new
│   ├── kill-criteria-design/SKILL.md         # new
│   └── citation-discipline/SKILL.md          # cross-cutting; cite or flag, never fabricate
├── .mcp.json                     # edgartools, yfinance, fred
├── samples/
│   └── COST/                     # one committed worked example
│       ├── fundamentals.json
│       ├── ... (all envelope files)
│       └── report.md
├── LICENSE                       # Apache-2.0
├── NOTICE                        # attributions
├── README.md
└── .gitignore                    # excludes research/
```

## 8. Capability inventory — reuse / port / skip

### Reuse from financial-services (Apache-2.0)

| Asset | Use as |
|---|---|
| `equity-research/skills/initiating-coverage/SKILL.md` | Reference shape for synthesizer skill structure |
| `equity-research/skills/thesis-tracker/SKILL.md` | Reference for `/revisit` command |
| `equity-research/skills/sector-overview/SKILL.md` | Reference for macro-secular subagent |
| `financial-analysis/skills/dcf-model/SKILL.md` | Adapt to **long-horizon-dcf** (normalized earnings, terminal-value-driven) |
| `financial-analysis/skills/comps-analysis/SKILL.md` | Adapt to **long-horizon-comps** (through-cycle multiples) |
| `financial-analysis/skills/competitive-analysis/SKILL.md` | Reference for moat-assessment skill |
| `financial-analysis/commands/dcf.md` | Reference for command-loads-skill pattern |

### Port concepts/prompts from InvestAgents (Apache-2.0)

| Concept | Port to |
|---|---|
| Bull/bear debate prompts | `bull-researcher.md`, `bear-researcher.md` agents (re-aimed at long horizon) |
| 3-way risk debate prompts | `aggressive-debator.md`, `conservative-debator.md`, `neutral-debator.md` agents |
| Trader/Portfolio Manager judging prompts | `synthesizer.md` (merged role; verdict + sizing in one agent) |
| Memory log / `past_context` injection | `history.md` per ticker + `/revisit` command |
| Structured-output Pydantic schemas | JSON envelope schema (§ 4.4) and verdict schema (§ 4.5) |

### Skip from financial-services

IB, PE, wealth-management, KYC, GL, month-end-close, earnings-analysis (short-cycle), morning-note, catalyst-calendar, model-update, xlsx-author, pptx-author.

### Skip from InvestAgents

LangGraph wiring, `tradingagents/graph/`, `dataflows/` (replaced by MCP), CLI TUI, checkpoint SQLite, all "online_tools" and "deep_thinking_llm vs quick_thinking_llm" plumbing (replaced by per-agent model choice in agent frontmatter).

## 9. Cost discipline

- **Default models**: Sonnet for the 10 analyst/researcher/debator calls; Opus for synthesizer.
- **Caching**: per-ticker analyst outputs cached for 24h on disk; `/revisit` reuses analyst files unless `--refresh`.
- **Token caps**: each analyst envelope `content` ≤ 4k tokens; synthesizer `report.md` ≤ 8k. Enforced in agent prompts.
- **Cost log**: synthesizer writes per-call token counts and total $ estimate to `history.md`.
- **Budget assumption**: ≤ $1 per analyst call (per user clarification needed; see § 12).

## 10. Apache-2.0 attribution checklist

- [ ] Top-level `LICENSE` = Apache-2.0 verbatim.
- [ ] `NOTICE` lists: financial-services (Anthropic), InvestAgents (Bence Olah), with copyright lines and "Modified from" attributions.
- [ ] Every ported file (skill, agent, command) carries a header comment: `# Modified from <source>/<path> (Apache-2.0). See NOTICE.`
- [ ] No Anthropic branding (no "Powered by Claude", no Anthropic logos, no marketing copy from upstream).
- [ ] README links to both upstream repos and their licenses.
- [ ] Changelog notes which prompts/skills are derivative vs original.

## 11. Risks, weakest assumptions

1. **Verdict overconfidence** — adding more analysts may make the verdict more *confident* without making it more *correct*. Mitigations: confidence gate (≥7), kill-criteria as testable lagging indicators, dissent-summary in the verdict.
2. **Citation discipline drift** — agents will be tempted to write plausible numbers without citations. Mitigations: citation-discipline skill loaded by every agent; synthesizer rejects any analyst envelope with uncited claims in `content`.
3. **EU mode is a footgun** — users may run EU tickers and not notice the degraded flag. Mitigations: refuse Initiate/Add for EU without explicit `--accept-eu-degraded`.
4. **MCP availability** — EdgarTools / FRED MCP servers may have rate limits or downtime. Mitigations: `gaps[]` entries on failure; synthesizer treats missing data as "do not Initiate" rather than "fabricate".
5. **The 3-way risk debate may be theater** — three LLM personas reading the same files may converge to the synthesizer's prior. Mitigations: per-debator prompts include explicit hard biases (aggressive must argue for entry; conservative must argue for caution; neutral reconciles); evaluate after first 5 sample runs whether the debate adds signal.
6. **Cost runaway** — 11 calls per ticker + Opus synthesizer + retries can exceed budget. Mitigations: token caps in prompts, cost log in `history.md`, hard-cap retries at 1.

## 12. Open questions (carried forward)

1. **Budget interpretation** — user wrote "1$ per token max"; spec assumes "$1 per analyst call max" (~$11/ticker). Confirm or override.
2. **InvestAgents prompt port** — license confirmed Apache-2.0 (verified). Attribution headers will reference `github.com/bolah/InvestAgents` commit SHA at port time.
3. **Sample ticker for committed `samples/`** — placeholder is COST; user choice welcome.

## 13. Out-of-band: what this design does NOT include

- No execution path. No broker. No portfolio state.
- No multi-ticker comparison in v1 (single ticker per `/analyze`).
- No backtest of past verdicts (v2: `history.md` accumulates the data needed for this).
- No Streamlit / web UI. CLI only.
- No automatic refresh / cron. User invokes `/analyze` and `/revisit` manually.
