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
