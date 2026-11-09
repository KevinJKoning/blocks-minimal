"""Every listing as recorded: nothing is screened out.

The option to beat. A listing with a price ten times too high is then one more point at ten
times its neighbourhood's value, and whatever averages the neighbourhood moves with it.
"""
from blocks import ui

METRICS = {"dropped": "listings screened out", "kept": "listings kept"}


def screen(clean):
    rows = clean["rows"]
    return {"rows": rows, "dropped": 0, "kept": len(rows), "dropped_rows": []}


def view(out):
    return [
        ui.metrics(),
        ui.markdown(f"Nothing is screened out: all **{out['kept']:,}** priceable listings go on to the estimate, the "
                    "factor-of-10 errors among them."),
    ]
