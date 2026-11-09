"""The store-week panel: each store's weekly sales, and whether the store ran the promotion.

The sales file has one row per store and week. A store is treated when it ran the promotion in
any week. The promotion's weeks are also the year's peak, so comparing them with the rest of the
year mixes the promotion with the season: the chart shows both groups' average sales week by week.
"""
import numpy as np
import pyarrow as pa
import pyarrow.csv as csv

from blocks import ui

METRICS = {"stores": "stores", "treated_stores": "treated stores", "store_weeks": "store-weeks",
           "promo_store_weeks": "promoted store-weeks"}


def prepare(sales):
    t = csv.read_csv(sales)
    store = t["store"].to_pylist()
    week = t["week"].to_numpy()
    promo = t["promo"].to_numpy()
    sold = t["sales"].to_numpy()
    ran = {s for s, p in zip(store, promo) if p}
    treated = np.array([s in ran for s in store], dtype=np.int64)
    table = pa.table({"store": store, "size_m2": t["size_m2"].to_numpy(), "week": week, "promo": promo,
                      "treated": treated, "sales": sold})
    weekly = {"treated": [float(sold[(treated == 1) & (week == w)].mean()) for w in range(1, 53)],
              "untreated": [float(sold[(treated == 0) & (week == w)].mean()) for w in range(1, 53)]}
    return {"table": table, "weekly": weekly, "stores": len(set(store)), "treated_stores": len(ran),
            "store_weeks": len(store), "promo_store_weeks": int(promo.sum())}


def view(out):
    w = out["weekly"]
    return [
        ui.download("sales_panel.csv", out["table"], title="every store-week, with whether its store was treated"),
        ui.metrics(),
        ui.markdown("Weeks 45 to 52 are the promotion's in the treated stores. They are also the year's peak, "
                    "so their gap to the untreated stores is not the promotion alone."),
        ui.chart(list(range(1, 53)), {"treated stores": w["treated"], "untreated stores": w["untreated"]},
                 title="Average weekly sales per store", x_label="week", y_label="sales per store"),
    ]
