"""The two ACS five-year periods every comparison runs between, named by their final year.

The periods do not overlap; population and demographics still show all three for context.
"""
from typing import Annotated
from blocks import Choices, ui
from demography import period


def periods(*, start_year: Annotated[int, Choices(2014, 2019)] = 2014,
            end_year: Annotated[int, Choices(2019, 2024)] = 2024):
    if start_year >= end_year:
        raise ValueError('The start period must come before the end period')
    return {'start_year': start_year, 'end_year': end_year, 'span': f'{period(start_year)} → {period(end_year)}'}


def view(out):
    return [ui.markdown(f"**{out['span']}**")]
