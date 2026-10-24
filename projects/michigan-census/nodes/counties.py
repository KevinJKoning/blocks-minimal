"""Where population changed across Michigan's 83 counties.

Each point is a county. Compare starting population with percentage change to
see whether growth is concentrated in large or small places. The table is sorted
by percentage change; ranks are descriptive and do not test statistical differences.
The full CSV includes both endpoint estimates and their published 90% MOEs.
"""
from blocks import ui
from demography import population, period

METRICS = {'growing': 'Counties with a population gain', 'declining': 'Counties with a population loss'}


def counties(ingest, periods):
    start, end = periods['start_year'], periods['end_year']
    a = {r['geoid']: r for r in ingest['rows'] if r['year'] == start and r['geoid'].startswith('050')}
    rows = []
    for b in ingest['rows']:
        if b['year'] != end or b['geoid'] not in a:
            continue
        first = a[b['geoid']]
        x, y = population(first), population(b)
        rows.append({'county': b['name'], 'geoid': b['geoid'], 'start_population': x, 'end_population': y,
                     'start_moe_90': first['tables']['B01001']['moe'][0], 'end_moe_90': b['tables']['B01001']['moe'][0],
                     'change': y - x, 'change_pct': 100 * (y / x - 1)})
    rows.sort(key=lambda r: (-r['change_pct'], r['geoid']))
    return {'rows': rows, 'growing': sum(r['change'] > 0 for r in rows),
            'declining': sum(r['change'] < 0 for r in rows), 'start': period(start), 'end': period(end)}


def view(out):
    rows = out['rows']
    return [ui.download('county-population-changes.csv', [{'start_period': out['start'], 'end_period': out['end'], **r} for r in rows]), ui.metrics(),
            ui.chart([r['start_population'] for r in rows], {'County': [r['change_pct'] for r in rows]}, kind='scatter',
                     title=f"County size and population change · {out['start']} → {out['end']}", x_label='Starting population', y_label='Population change (%)'),
            ui.table(rows, title='All 83 counties, sorted by percentage change')]
