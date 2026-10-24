"""Load the Titanic passenger records into a Python table.

Reads the original CSV in the browser and preserves every row and column. Blank
cells become nulls; no passengers are dropped and no missing values are filled.
The table is available to subsequent nodes for exploration and modelling.
"""
import pyarrow.csv as csv

from blocks import ui

METRICS = {
    "n_passengers": "Passengers loaded",
    "n_columns": "Columns",
    "n_missing": "Missing cells",
}


def ingest(passengers):
    table = csv.read_csv(passengers, convert_options=csv.ConvertOptions(strings_can_be_null=True))
    missing = [{"column": name, "missing": column.null_count}
               for name, column in zip(table.column_names, table.columns)]
    return {"table": table, "n_passengers": table.num_rows, "n_columns": table.num_columns,
            "n_missing": sum(row["missing"] for row in missing), "missing": missing}


def view(out):
    return [
        ui.metrics(),
        ui.markdown("All passenger records retained. Missing values are preserved for the next analysis step."),
        ui.table(out["table"], title="Passenger data"),
        ui.table(out["missing"], title="Missing values by column"),
    ]
