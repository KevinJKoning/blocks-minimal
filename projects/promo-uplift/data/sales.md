Weekly sales per store, one row per store and week, as a single CSV (`sales.csv`).

| column | means |
|---|---|
| `store` | the store's code |
| `size_m2` | the store's floor area, in square metres |
| `week` | the week of the year, 1 to 52 |
| `promo` | 1 if the store ran the promotion that week, else 0 |
| `sales` | the store's sales that week, in the retailer's currency |

Twenty of the forty stores ran the promotion in weeks 45 to 52 and no others did. To use real
data, replace the file with an export of the same columns: every store, every week, with
`promo` set where the promotion ran.
