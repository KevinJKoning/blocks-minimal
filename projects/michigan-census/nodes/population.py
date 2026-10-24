"""Population over three non-overlapping five-year periods.

The chosen geography's point estimates are connected only to guide the eye;
there are no annual observations between them. The table preserves published
90% margins of error. A null MOE can mean a controlled estimate, not no uncertainty.
"""
from blocks import ui
from demography import period, population as count

METRICS = {'latest_population': 'Population at comparison end', 'change': 'Population change',
           'change_pct': 'Population change (%)'}


def population(geography, periods):
    rows = [{'period': period(r['year']), 'end_year': r['year'], 'population': count(r),
             'moe_90': r['tables']['B01001']['moe'][0]} for r in geography['rows']]
    a, b = [next(r for r in rows if r['end_year'] == y) for y in [periods['start_year'], periods['end_year']]]
    return {'rows': rows, 'name': geography['name'], 'latest_population': b['population'],
            'change': b['population'] - a['population'],
            'change_pct': 100 * (b['population'] / a['population'] - 1)}


def view(out):
    rows = out['rows']
    return [ui.download('population.csv', [{'geography': out['name'], **r} for r in rows]), ui.metrics(),
            ui.chart([r['end_year'] for r in rows], {out['name']: [r['population'] for r in rows]},
                     title=f"{out['name']}: population", x_label='ACS five-year period ending', y_label='People', x_text=True),
            ui.table(rows, title='Population and published 90% margins of error', text=['end_year'])]
