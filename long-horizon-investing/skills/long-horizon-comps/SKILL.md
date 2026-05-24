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
  "peers": [],
  "subject_pe_normalized": null,
  "subject_ev_ebitda_normalized": null,
  "peer_pe_median_10y": null,
  "peer_ev_ebitda_median_10y": null,
  "pe_premium_discount_pct": null,
  "ev_ebitda_premium_discount_pct": null,
  "comps_verdict": "expensive|in_line|cheap|mixed"
}
```
