---
name: citation-discipline
description: Enforce citation-or-flag discipline for all numerical claims in research outputs. Load this skill in every agent that writes to a research envelope file.
---

# Citation Discipline

## The Rule

Every numerical claim written to the `content` block of a research envelope MUST have a corresponding entry in the `citations[]` array.

If you cannot cite a number — because the MCP tool returned no data, the ticker is EU-only and EDGAR is unavailable, or the source is ambiguous — you MUST:

1. Write the gap to the `gaps[]` array: `"data not available: [what and why]"`
2. Omit the number from `content` entirely
3. Never substitute a plausible estimate, a rounded figure, or a "typically around X" guess

## What counts as a numerical claim

Any claim of quantity, magnitude, rank, or trend — including but not limited to:
- Revenue, earnings, margin, multiple, ratio, growth rate, yield, or price
- Any date range used in trend statements ("over the past 10 years...")
- Any ranking, market-share, count, or size figure ("17,000 employees", "top-2 player")
- Any categorical claim derived from data ("above-average retention") — cite the source data

## Citation format

Each entry in `citations[]`:
```json
{
  "claim": "10-year average ROIC = 18.3%",
  "source": "edgar",
  "url_or_id": "COST 10-K 2024, SEC CIK 895126",
  "retrieved_at": "YYYY-MM-DD"
}
```

Valid `source` values: `edgar`, `yfinance`, `fred`, `web`, `computed`.
- `computed` = value derived by arithmetic from other cited sources (e.g., "10y median margin computed from 10 annual EDGAR filings"). The individual source filings must also have their own citations[] entries.

**One citations[] entry per claim**, even if multiple claims share the same source document.

## EU mode

If the ticker is not listed on a US exchange and EdgarTools returns no filings:
- Set `eu_mode_degraded: true` at the envelope top level
- Add to `gaps[]`: `"EU mode: EDGAR unavailable; insider/13F data absent; fundamentals from yfinance only"`
- Do NOT fabricate EDGAR-equivalent numbers from yfinance

**Partial coverage** (cross-listed tickers or < 3 years of 10-K filings): treat affected fields as degraded, note in `gaps[]` which specific fields used EDGAR vs. yfinance fallback.

## Confidence scale

`confidence` is an integer 1–10:
- **1–3**: Most content fields are null or in gaps[] (data-poor run, e.g., EU mode or MCP failure)
- **4–6**: Mix of cited fields and gaps; meaningful but incomplete analysis
- **7–9**: Most fields have citations; a few minor gaps
- **10**: Every field in `content` has a citations[] entry; no gaps

## Self-check before writing the file

Before writing the envelope JSON, run this mental checklist:
1. Every number in `content` has a matching `citations[]` entry — yes/no?
2. Every unavailable data point is in `gaps[]` — yes/no?
3. `confidence` (1–10) accurately reflects the fraction of `content` that is cited vs. null/in-gaps — is it scored correctly? yes/no?

If any answer is no, fix it before writing.
