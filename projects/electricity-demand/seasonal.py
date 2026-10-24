"""The seasonal model's design matrix, shared by fit and forecast."""
import numpy as np


def design(t, season_length):
    """Columns for months t (0 = the first month of history): t, then one indicator per
    position in the season."""
    t = np.asarray(t)
    return np.column_stack([t, np.eye(season_length)[t % season_length]])
