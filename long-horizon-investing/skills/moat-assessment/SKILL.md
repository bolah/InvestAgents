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
   Use the WACC from `valuation.json` if already written; otherwise use a sector-median proxy of 9% and note in `gaps[]`: "WACC estimated at 9% sector-median proxy; not derived from company-specific inputs."
3. Run a web search for analyst moat assessments, Morningstar moat ratings if available, and competitor positioning.
   If no Morningstar rating is found, document absence in `gaps[]` and rely on the quantitative ROIC evidence.
4. Score each source with evidence. Cite every score.
5. State the overall moat verdict: wide / narrow / none, with a one-sentence rationale.

## Output block (goes into moat.json `content`)

Total `moat_score_total` must equal the sum of the five source scores (0–10 max).

```json
{
  "moat_verdict": "wide|narrow|none",
  "moat_score_total": 0,
  "sources": {
    "network_effects": { "score": 0, "evidence": "cite source + 1-2 sentence justification" },
    "intangible_assets": { "score": 0, "evidence": "cite source + 1-2 sentence justification" },
    "cost_advantage": { "score": 0, "evidence": "cite source + 1-2 sentence justification" },
    "switching_costs": { "score": 0, "evidence": "cite source + 1-2 sentence justification" },
    "efficient_scale": { "score": 0, "evidence": "cite source + 1-2 sentence justification" }
  },
  "roic_10y_avg": null,
  "roic_trend": "improving|stable|declining|insufficient_data",
  "moat_durability_horizon": "< 5y|5-10y|> 10y|unknown"
}
```
