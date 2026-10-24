import base64
import io
import json
import os

from ._kit import block, plain, tabulate

TYPES = {".csv": "text/csv", ".json": "application/json", ".md": "text/markdown", ".txt": "text/plain",
         ".parquet": "application/vnd.apache.parquet", ".svg": "image/svg+xml", ".png": "image/png"}


def download(name, value, title=None):
    """A file to take away, by extension: a table as .csv, .json or .parquet; text; bytes.
    The overview gathers every node's downloads (one of the two blocks the core names)."""
    ext = os.path.splitext(name)[1].lower()
    if isinstance(value, (bytes, bytearray)):
        data = bytes(value)
    elif isinstance(value, str):
        data = value.encode()
    elif ext == ".parquet":
        import pyarrow as pa
        import pyarrow.parquet as pq
        cols, rows = tabulate(value)
        buf = io.BytesIO()
        pq.write_table(pa.table({c: [r[i] for r in rows] for i, c in enumerate(cols)}), buf)
        data = buf.getvalue()
    elif ext == ".csv":
        import csv
        cols, rows = tabulate(value)
        out = io.StringIO()
        w = csv.writer(out, lineterminator="\n")
        w.writerow(cols)
        w.writerows([["" if x is None or x != x else x for x in r] for r in plain(rows)])
        data = out.getvalue().encode()
    else:
        data = json.dumps(plain(value), indent=1, default=str).encode()
    return block("download", name=str(name), title=title, media=TYPES.get(ext, "application/octet-stream"),
                 size=len(data), data=base64.b64encode(data).decode())
