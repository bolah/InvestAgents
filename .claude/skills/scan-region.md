---
name: scan-region
description: Run a fully automated country/region scan — macro backdrop, sector scoring, and ETF verdict. Use when the user invokes /scan-region or asks to scan a country or region for equity investment opportunities.
---

Run the full region scan pipeline for a given country or region. The pipeline has three stages: parallel macro + ETF scouting, parallel sector scoring, and synthesis.

## Step 1: Get the region name

Parse the region name from the user's message or skill args. If not provided, ask: "Which country or region would you like to scan?"

## Step 2: Compute region slug

Lowercase the region name and replace spaces with underscores.
- "South Korea" → `south_korea`
- "Southeast Asia" → `southeast_asia`

Create the output directory: `research/{region_slug}/`

## Step 3: Stage 1 — Parallel bootstrap

Dispatch both agents simultaneously using the Agent tool:

- `long-horizon-investing:country-macro` agent with prompt:
  > "Assess the macro and demographic backdrop for {REGION} for long-horizon equity investing. Research directory: research/{region_slug}/"

- `long-horizon-investing:region-scout` agent with prompt:
  > "Find the primary ETF and top holdings for {REGION}. Research directory: research/{region_slug}/"

Wait for **both** to complete before proceeding.

## Step 4: Check for scout error

Read `research/{region_slug}/scout.json`. Check `content.error`.

If `content.error` is not null, display this message and halt:

```
⚠️  Region scout could not resolve a primary ETF for "{REGION}".
    {content.suggestion if present}
    Please narrow the region name or specify a country directly.
```

## Step 5: Stage 2 — Sector screeners

Read `research/{region_slug}/scout.json`. Extract sector names from `content.sectors[*].name`.

Dispatch one `long-horizon-investing:sector-screener` agent **per sector** simultaneously:

For each sector name:
- Agent prompt: `"sector-screener for the {sector_name} sector in {REGION}. Research directory: research/{region_slug}/"`

Wait for **all** to complete before proceeding.

## Step 6: Stage 3 — Synthesis

Dispatch `long-horizon-investing:region-synthesizer` with prompt:
> "Synthesize the region scan for {REGION} (slug: {region_slug}). Research directory: research/{region_slug}/"

Wait for it to complete.

## Step 7: Display the brief

Read `research/{region_slug}/brief.md` and display the full contents to the user.
