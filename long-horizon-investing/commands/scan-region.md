---
description: Run a fully automated country/region scan — macro backdrop, sector scoring, and ETF verdict.
argument-hint: '"Country or Region Name"'
---

# /scan-region "Country or Region Name"

Run a full region scan pipeline for the given country or region.

**Usage:**
- `/scan-region "South Korea"` — full scan, all sectors
- `/scan-region "Brazil"` — single country scan
- `/scan-region "Southeast Asia"` — multi-country regional scan

## Steps

1. Parse the region name from the argument. If no region name was provided, ask for one.

2. Compute the region slug: lowercase the region name and replace spaces with underscores.
   - "South Korea" → `south_korea`
   - "Southeast Asia" → `southeast_asia`

3. Create the output directory: `research/{region_slug}/`

4. **Stage 1 — Parallel bootstrap (run both simultaneously):**

   Dispatch both agents at the same time using the Agent tool:

   - `country-macro` agent with prompt:
     > "Assess the macro and demographic backdrop for {REGION} for long-horizon equity investing. Research directory: research/{region_slug}/"

   - `region-scout` agent with prompt:
     > "Find the primary ETF and top holdings for {REGION}. Research directory: research/{region_slug}/"

   Wait for **both** to complete before proceeding.

5. **Check for scout error:**

   Read `research/{region_slug}/scout.json`. Check `content.error`.

   If `content.error` is not null, display this message and halt:

   ```
   ⚠️  Region scout could not resolve a primary ETF for "{REGION}".
       {content.suggestion if present}
       Please narrow the region name or specify a country directly.
   ```

6. **Stage 2 — Sector screeners (run all simultaneously):**

   Read `research/{region_slug}/scout.json`. Extract the sector list from `content.sectors[*].name`.

   Dispatch one `sector-screener` agent **per sector** simultaneously using the Agent tool:

   For each sector name in the list:
   - Agent prompt: `"sector-screener for the {sector_name} sector in {REGION}. Research directory: research/{region_slug}/"`

   Wait for **all** sector screeners to complete before proceeding.

7. **Stage 3 — Synthesis (sequential):**

   Run `region-synthesizer` agent with prompt:
   > "Synthesize the region scan for {REGION} (slug: {region_slug}). Research directory: research/{region_slug}/"

   Wait for it to complete.

8. **Display the brief:**

   Read `research/{region_slug}/brief.json` and `research/{region_slug}/brief.md` and display the full contents to the user.
