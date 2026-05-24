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

## Output block (goes into valuation.json `content.dcf`)

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
