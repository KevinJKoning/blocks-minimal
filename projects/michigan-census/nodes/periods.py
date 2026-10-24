"""The two ACS five-year periods every comparison runs between.

The periods do not overlap; population and demographics still show all three for context.
"""
from typing import Annotated
from blocks import Choices, ui


def periods(*, comparison: Annotated[str, Choices(
        '2010–2014 → 2020–2024', '2010–2014 → 2015–2019', '2015–2019 → 2020–2024')] = '2010–2014 → 2020–2024'):
    start, end = (int(p.split('–')[1]) for p in comparison.split(' → '))
    return {'start_year': start, 'end_year': end, 'span': comparison}


def view(out):
    return [ui.markdown(f"**{out['span']}**")]
