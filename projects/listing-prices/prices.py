"""What the listing nodes share: reading the listings, grouping them, and splitting them."""
import csv


def read(path):
    """The listings as rows, in file order: area_m2 is None where the listing gives none."""
    with open(path, newline="") as f:
        return [{"listing_id": r["listing_id"], "neighbourhood": r["neighbourhood"], "listed": r["listed"],
                 "price": float(r["price"]), "area_m2": float(r["area_m2"]) if r["area_m2"] else None}
                for r in csv.DictReader(f)]


def by_neighbourhood(rows):
    """{neighbourhood: [per_m2, ...]}, in name order."""
    groups = {}
    for r in rows:
        groups.setdefault(r["neighbourhood"], []).append(r["per_m2"])
    return dict(sorted(groups.items()))


def split(rows, keep):
    """(kept, dropped): the rows keep(row) is true of, and the rest, each in file order."""
    flags = [bool(keep(r)) for r in rows]
    return [r for r, k in zip(rows, flags) if k], [r for r, k in zip(rows, flags) if not k]
