"""Stable Census table definitions; line numbers are one-based in source documentation."""
AGE = {
    'Under 18': list(range(3, 7)) + list(range(27, 31)),
    '18–64': list(range(7, 20)) + list(range(31, 44)),
    '65 and older': list(range(20, 26)) + list(range(44, 50)),
}
RACE = {
    'White alone, non-Hispanic': [3],
    'Black alone, non-Hispanic': [4],
    'American Indian / Alaska Native alone, non-Hispanic': [5],
    'Asian alone, non-Hispanic': [6],
    'Native Hawaiian / Pacific Islander alone, non-Hispanic': [7],
    'Other race alone, non-Hispanic': [8],
    'Two or more races, non-Hispanic': [9],
    'Hispanic / Latino, any race': [12],
}


def estimate(row, table, lines):
    return sum(row['tables'][table]['estimate'][i - 1] for i in lines)


def population(row):
    return estimate(row, 'B01001', [1])


def period(year):
    return f'{year - 4}–{year}'
