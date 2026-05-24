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
  Derive WACC from `valuation.json` if already written; otherwise estimate from FRED GS10 (risk-free rate) + 5.5% equity risk premium + yfinance 5y beta. Cite the WACC source in `citations[]`.
- Label each year: value-creating (ROIC > WACC + 1pp), neutral (within ±1pp of WACC), or value-destroying (ROIC < WACC - 1pp)

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
  "roic_10y_series": [{"year": 2015, "roic_pct": 18.3}, "..."],
  "roic_vs_wacc_verdict": "consistently_above|mixed|consistently_below|insufficient_data",
  "buyback_discipline": "counter_cyclical|neutral|pro_cyclical|no_buybacks",
  "dividend_policy": "growing|stable|variable|no_dividend|cut_history",
  "acquisition_track_record": "value_additive|neutral|value_destructive|no_acquisitions",
  "mgmt_insider_ownership_pct": null
}
```
