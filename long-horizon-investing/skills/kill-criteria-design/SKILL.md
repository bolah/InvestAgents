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
| Management | "CEO and CFO both depart within 12 months AND no named internal successor announced within 90 days of first departure" | Web/press |

## Output format (goes into verdict.json `kill_criteria[]`)

```json
[
  {
    "trigger": "ROIC falls below WACC for 2 consecutive fiscal years",
    "lagging_indicator": "EDGAR 10-K: NOPAT / invested capital < 8.5% (estimated WACC) in FY25 and FY26",
    "review_cadence": "annual"
  },
  "... (repeat for each of your 3-6 criteria)"
]
```

Write 3–6 kill-criteria. Fewer is better if each one is precise. Vague kill-criteria are worse than none.
