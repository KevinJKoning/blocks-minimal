"""Validate the Census snapshot before any comparisons.

The project refresh script retrieves official ACS bulk files. This node checks one
Michigan record and all 83 counties in each release, table widths, nonnegative
estimates, consistent population totals, and exhaustive age and race partitions.
Missing or special margins of error remain null, never zero. State names for the
2024 files come from the 2019 geographic file; the county FIPS set is checked.
"""
import json
import math
from blocks import ui
from demography import AGE, RACE, estimate, population

METRICS = {'records': 'Geography-period records', 'missing_moes': 'Unavailable margin-of-error cells'}


def ingest(census):
    with open(census) as f:
        snapshot = json.load(f)
    rows = snapshot['rows']
    expected = {2014, 2019, 2024}
    if set(r['year'] for r in rows) != expected or len(rows) != 252:
        raise ValueError('Expected 252 records across 2014, 2019, and 2024')
    keys = [(r['year'], r['geoid']) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate geography-period records')
    geo_sets = [{r['geoid'] for r in rows if r['year'] == y} for y in sorted(expected)]
    if any(g != geo_sets[0] for g in geo_sets):
        raise ValueError('Geographies differ between releases')
    if '04000US26' not in geo_sets[0] or sum(g.startswith('05000US26') for g in geo_sets[0]) != 83:
        raise ValueError('Expected Michigan and its 83 counties')
    missing = 0
    for row in rows:
        for table, width in [('B01001', 49), ('B03002', 21)]:
            t = row['tables'][table]
            if any(len(t[field]) != width for field in ['estimate', 'moe']):
                raise ValueError(f'Wrong table width: {row["geoid"]} {table}')
            if any(v is None or not math.isfinite(v) or v < 0 for v in t['estimate']):
                raise ValueError(f'Missing or invalid estimate: {row["geoid"]} {table}')
            if any(v is not None and (not math.isfinite(v) or v < 0) for v in t['moe']):
                raise ValueError('Invalid margin of error')
            missing += sum(v is None for v in t['moe'])
        total = population(row)
        if total <= 0 or estimate(row, 'B03002', [1]) != total:
            raise ValueError('Population universes disagree')
        if sum(estimate(row, 'B01001', lines) for lines in AGE.values()) != total:
            raise ValueError('Age groups do not sum to population')
        if sum(estimate(row, 'B03002', lines) for lines in RACE.values()) != total:
            raise ValueError('Race/ethnicity groups do not sum to population')
    return {'rows': rows, 'sources': snapshot['sources'], 'retrieved_at': snapshot['retrieved_at'],
            'records': len(rows), 'missing_moes': missing}


def view(out):
    return [ui.download('census-sources.json', {'sources': out['sources'], 'retrieved_at': out['retrieved_at']}),
            ui.metrics(),
            ui.markdown(f"Retrieved **{out['retrieved_at']}**. Population is a period estimate, "
                        'not a decennial count or a July 1 population estimate.'),
            ui.table([{'url': s['url'], 'sha256': s['sha256']} for s in out['sources']], title='Source files')]
