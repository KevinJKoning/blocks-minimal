"""Each territory as a tile, highest rate first: its name, its base rate and how credible its
experience is. A block only windstorm draws."""

# The cut-offs credibility's metrics use: Z < 0.1 is mostly the GLM's, Z ≥ 0.9 mostly its own.
BANDS = [(0.1, "low"), (0.9, "medium"), (float("inf"), "high")]


def tiles(names, rates, z, title=None):
    order = sorted(range(len(rates)), key=lambda i: -rates[i])
    return {"type": "tiles", "title": title,
            "tiles": [{"name": str(names[i]), "rate": float(rates[i]), "band": next(b for cut, b in BANDS if z[i] < cut)}
                      for i in order]}
