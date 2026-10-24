"""Territory base rates: the GLM's frequency for a reference home, adjusted by credibility.

The reference home is frame construction with a 10-year-old roof and a 1,000 deductible,
at the centre of the territory (its distance inland and its terrain). Its GLM frequency,
times the territory's credibility-weighted θ, is the territory's base rate; every other home
is rated from it with the GLM's relativities. Every territory gets a rate, the empty ones
too: with no experience, Z = 0 and the GLM alone sets it.
"""
import numpy as np
import pyarrow as pa

from blocks import ui
from rating import design

METRICS = {"lowest": "lowest rate per 1,000 homes", "highest": "highest rate per 1,000 homes",
           "spread": "highest / lowest"}


def rates(join, wind, glm, credibility):
    t, c = join["territories"], credibility["table"]
    n = t.num_rows
    X = design(["frame"] * n, [10] * n, [1000] * n, t["terrain"].to_numpy(zero_copy_only=False))
    beta = np.array([b["estimate"] for b in glm["coefficients"]])
    base = np.exp(X @ beta + wind["territory_offset"]) * 1000
    rate = base * c["theta"].to_numpy()
    table = pa.table({"territory": t["territory"], "terrain": t["terrain"], "km_inland": np.round(t["distance_km"].to_numpy(), 1),
                      "policy_years": np.round(t["policy_years"].to_numpy(), 1), "claims": t["claims"],
                      "z": np.round(c["z"].to_numpy(), 3), "glm_rate": np.round(base, 2), "rate": np.round(rate, 2)})
    return {"table": table, "wkb": t["wkb"], "lowest": float(rate.min()), "highest": float(rate.max()),
            "spread": float(rate.max() / rate.min())}


def view(out):
    t = out["table"]
    return [
        ui.download("territory_rates.csv", t, title="every territory's base rate, its GLM rate and its credibility"),
        ui.metrics(),
        ui.map(out["wkb"], t["rate"], names=t["territory"],
               title="Base rate: windstorm claims per 1,000 reference homes a year", label="per 1,000"),
        ui.table(t.sort_by([("rate", "descending")]), title="Territories, highest rate first"),
    ]
