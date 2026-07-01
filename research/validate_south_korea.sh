#!/usr/bin/env bash
# Smoke test validation for /scan-region "South Korea"
# Run this AFTER running /scan-region "South Korea" in a Claude Code session with the plugin loaded.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Smoke test: /scan-region South Korea ==="

echo ""
echo "--- Step 1: Check output files exist ---"
ls research/south_korea/

echo ""
echo "--- Step 2: Validate scout.json ---"
python3 -c "
import json
d = json.load(open('research/south_korea/scout.json'))
c = d['content']
assert c['error'] is None, f'Scout error: {c[\"error\"]}'
assert len(c['sectors']) >= 2, f'Expected >=2 sectors, got {len(c[\"sectors\"])}'
for s in c['sectors']:
    assert 'name' in s
    assert 'sector_slug' in s
    assert len(s['stocks']) >= 3, f'Sector {s[\"name\"]} has <3 stocks'
print('scout.json OK —', len(c['sectors']), 'sectors found:', [s['name'] for s in c['sectors']])
"

echo ""
echo "--- Step 3: Validate sector files ---"
python3 -c "
import json, glob
files = glob.glob('research/south_korea/sector_*.json')
assert len(files) >= 2, f'Expected >=2 sector files, got {len(files)}'
for f in files:
    d = json.load(open(f))
    c = d['content']
    assert 'composite_score' in c, f'{f}: missing composite_score'
    assert 'edge' in c, f'{f}: missing edge'
    assert 'fundamentals_score' in c, f'{f}: missing fundamentals_score'
    assert isinstance(c['narrative_risks'], list), f'{f}: narrative_risks not a list'
    print(f\"  {d['sector']}: composite={c['composite_score']:.1f}, edge={c['edge']}, narrative_risks={len(c['narrative_risks'])}\")
print('All sector files OK')
"

echo ""
echo "--- Step 4: Validate brief.json and brief.md ---"
python3 -c "
import json
d = json.load(open('research/south_korea/brief.json'))
c = d['content']
assert c['verdict'] in ('Invest', 'Watch', 'Pass'), f'Invalid verdict: {c[\"verdict\"]}'
assert c['macro_backdrop'] in ('Supportive', 'Neutral', 'Headwind')
assert len(c['sector_scorecard']) >= 2
print('brief.json OK — verdict:', c['verdict'], '| macro:', c['macro_backdrop'])
print('Edge sectors:', c['edge_sectors'])
print('Instruments:', [i['etf_ticker'] for i in c['instruments']])
" && test -f research/south_korea/brief.md && echo "brief.md exists"

echo ""
echo "=== All validations passed ==="
