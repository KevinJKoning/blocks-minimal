"""County maps of population and demographic change.

All three maps show the 83 counties between the chosen periods; choose the measure for
the demographic maps here. The change maps diverge from zero, losses red-brown and gains
blue; each map has its own legend, and a county's name and value show on hover. Changes
in shares are percentage points, not percentage changes. Colours describe point
estimates, not statistical significance.
"""
from typing import Annotated
from blocks import Choices, ui
from demography import AGE, RACE, estimate, population, period


def maps(ingest, periods, shapes, *, measure: Annotated[str, Choices(
        '65 and older', 'Under 18', '18–64', 'Hispanic / Latino, any race',
        'White alone, non-Hispanic', 'Black alone, non-Hispanic',
        'Asian alone, non-Hispanic', 'Two or more races, non-Hispanic',
        'American Indian / Alaska Native alone, non-Hispanic',
        'Native Hawaiian / Pacific Islander alone, non-Hispanic',
        'Other race alone, non-Hispanic')] = '65 and older'):
    table, lines = ('B01001', AGE[measure]) if measure in AGE else ('B03002', RACE[measure])
    start, end = periods['start_year'], periods['end_year']
    a = {r['geoid']: r for r in ingest['rows'] if r['year'] == start and r['geoid'].startswith('050')}
    b = {r['geoid']: r for r in ingest['rows'] if r['year'] == end and r['geoid'].startswith('050')}
    if set(shapes['counties']) != set(a) or set(a) != set(b):
        raise ValueError('County boundaries must match all 83 Census county FIPS exactly')
    rows = []
    for geoid in shapes['counties']:
        first, last = a[geoid], b[geoid]
        x = 100 * estimate(first, table, lines) / population(first)
        y = 100 * estimate(last, table, lines) / population(last)
        rows.append({'county': last['name'], 'geoid': geoid, 'start_period': period(start),
                     'end_period': period(end), 'measure': measure,
                     'population_change_pct': 100 * (population(last) / population(first) - 1),
                     'start_share_pct': x, 'end_share_pct': y, 'share_change_pp': y - x})
    return {'rows': rows, 'shapes': list(shapes['counties'].values()), 'measure': measure,
            'start': period(start), 'end': period(end), 'span': periods['span']}


def view(out):
    rows, shapes, span = out['rows'], out['shapes'], out['span']
    names = [r['county'] for r in rows]
    return [ui.download('county-map-values.csv', rows),
            ui.map(shapes, [r['population_change_pct'] for r in rows], names=names,
                   title=f'Population change · {span}', label='Population change (%)', center=0),
            ui.row(ui.map(shapes, [r['end_share_pct'] for r in rows], names=names,
                          title=f"{out['measure']} · {out['end']}", label='Share (%)'),
                   ui.map(shapes, [r['share_change_pp'] for r in rows], names=names,
                          title=f"Share change · {span}", label='Change (pp)', center=0),
                   title=f"{out['measure']}: where the share is, and how it moved")]
