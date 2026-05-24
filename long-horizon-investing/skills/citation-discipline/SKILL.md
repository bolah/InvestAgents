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
