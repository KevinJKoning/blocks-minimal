Weekly sales for every store, as a **gzipped CSV** (`.csv.gz`: a replacement takes this file's
name, so it must be gzipped too), one row per store and week:

| column | means |
|---|---|
| `store` | the store's identifier |
| `week` | the week of the year, 1 to 52 |
| `treated` | 1 if the store ran the promotion (in the last 8 weeks), else 0 |
| `sales` | the store's sales that week, in dollars |

The promotion's weeks are not in the file: the app's `from_week` setting says where they start.
