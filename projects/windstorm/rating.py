"""The GLM's rating factors as design-matrix columns, shared by `glm` and `rates`."""
import numpy as np

# Base levels: frame construction, suburban terrain; roof age per decade; deductible as log(deductible / 1,000).
TERMS = ["intercept", "masonry", "concrete", "roof_age_per_decade", "log_deductible_per_1000", "urban", "open"]


def design(construction, roof_age, deductible, terrain):
    construction, terrain = np.asarray(construction), np.asarray(terrain)
    return np.column_stack([np.ones(len(construction)), construction == "masonry", construction == "concrete",
                            np.asarray(roof_age) / 10, np.log(np.asarray(deductible) / 1000),
                            terrain == "urban", terrain == "open"]).astype(float)
