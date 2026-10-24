"""How the chosen geography's age and race/ethnicity composition changed.

Age groups exhaust the population. Race/ethnicity categories also exhaust the
population: Hispanic/Latino includes any race; all other groups are non-Hispanic.
Shares are percentages of the total population; changes are percentage points.
Race coding and self-identification changed around 2020, especially for multiracial
and some-other-race responses. These shifts are not solely migration or births.
Charts show point estimates, not significance tests. Published source-cell 90%
MOEs are included in the download; no uncertainty claim is made for derived shares.
"""
from blocks import ui
from demography import AGE, RACE, estimate, population, period

METRICS = {'under18_pp': 'Under-18 share change (pp)', 'older_pp': '65+ share change (pp)'}


def demographics(geography, periods):
    rows = []
    source = []
    for r in geography['rows']:
        for family, table, groups in [('Age', 'B01001', AGE), ('Race / ethnicity', 'B03002', RACE)]:
            for group, lines in groups.items():
                n = estimate(r, table, lines)
                rows.append({'family': family, 'group': group, 'end_year': r['year'], 'period': period(r['year']),
                             'people': n, 'share_pct': 100 * n / population(r)})
            source.append({'year': r['year'], 'geoid': r['geoid'], 'table': table, **r['tables'][table]})
    changes = []
    for family, groups in [('Age', AGE), ('Race / ethnicity', RACE)]:
        for group in groups:
            a, b = [next(r for r in rows if r['group'] == group and r['end_year'] == year)
                    for year in [periods['start_year'], periods['end_year']]]
            changes.append({'family': family, 'group': group, 'start_share_pct': a['share_pct'],
                            'end_share_pct': b['share_pct'], 'change_pp': b['share_pct'] - a['share_pct'],
                            'people_change': b['people'] - a['people']})
    return {'start_period': period(periods['start_year']), 'end_period': period(periods['end_year']),
            'rows': rows, 'changes': changes, 'source': source, 'name': geography['name'],
            'under18_pp': changes[0]['change_pp'], 'older_pp': changes[2]['change_pp']}


def view(out):
    years = sorted({r['end_year'] for r in out['rows']})
    blocks = [ui.download('demographic-shares.csv', [{'geography': out['name'], **r} for r in out['rows']]),
              ui.download('demographic-changes.csv', [{'geography': out['name'], 'start_period': out['start_period'],
                                                        'end_period': out['end_period'], **r} for r in out['changes']]),
              ui.download('demographic-source-cells.json', out['source']), ui.metrics()]
    for family, groups in [('Age', AGE), ('Race / ethnicity', RACE)]:
        blocks.append(ui.chart(years, {g: [next(r['share_pct'] for r in out['rows'] if r['group'] == g and r['end_year'] == y)
                                          for y in years] for g in groups},
                               title=f"{out['name']}: {family.lower()} shares", x_label='ACS five-year period ending',
                               y_label='Share of population (%)', x_text=True))
        blocks.append(ui.table([r for r in out['changes'] if r['family'] == family], title=f'{family}: selected-period changes'))
    return blocks
