"""What the outlier options share: how far each listing's price per square metre is from the
city-wide level, and the band it must lie in to be taken at face value.

The city level is the median of every kept listing. A listing outside the band (more than
`band` times the level above, or below its 1/`band`) is off by a factor of 10 in the data,
not by the market: no neighbourhood is that far from the city, so the price is wrong.
"""
import numpy as np
import pyarrow as pa

from blocks import ui


def city_level(clean):
    return float(np.median(clean["table"]["price_per_m2"].to_numpy()))


def off_band(clean, band):
    """{listing_id, neighbourhood, price_per_m2, log_ratio, off} for every kept listing, where
    log_ratio is log10 of its price per m² over the city level, and off whether it is outside the band."""
    t = clean["table"]
    level = city_level(clean)
    ratio = np.asarray(t["price_per_m2"].to_numpy()) / level
    return {"listing_id": t["listing_id"].to_pylist(), "neighbourhood": t["neighbourhood"].to_pylist(),
            "price_per_m2": t["price_per_m2"].to_numpy(), "log_ratio": np.log10(ratio),
            "off": (ratio > band) | (ratio < 1 / band), "level": level}


def neighbourhoods(outliers):
    """The neighbourhoods' names (in order), their kept listings' counts and medians of price per
    m², and the city-wide median of every kept listing: what both estimates start from."""
    t = outliers["table"]
    names = np.array(t["neighbourhood"].to_pylist())
    price = t["price_per_m2"].to_numpy()
    rows = sorted(set(names.tolist()))
    n = np.array([np.sum(names == r) for r in rows], dtype=float)
    med = np.array([np.median(price[names == r]) for r in rows])
    return rows, n, med, float(np.median(price))


def estimates(rows, n, med, est, city):
    """An estimate option's output: each neighbourhood's listings, median and estimate."""
    table = pa.table({"neighbourhood": rows, "listings": n.astype(int), "median": med, "estimate": est})
    return {"table": table, "neighbourhoods": len(rows), "city_level": city, "thinnest": int(n.min())}


def show_estimates(out):
    """The view of an estimate option: a download, the metrics, the estimates, the table."""
    t = out["table"].sort_by([("estimate", "descending")])
    return [
        ui.download("neighbourhood_prices.csv", out["table"], title="each neighbourhood's estimated price per square metre"),
        ui.metrics(),
        ui.bars(t["neighbourhood"].to_pylist(), {"estimate": t["estimate"].to_pylist()}, kind="dot",
                title="Estimated price per square metre, highest first", label="price per m²"),
        ui.table(t, title="Neighbourhoods, highest estimate first", limit=100),
    ]
