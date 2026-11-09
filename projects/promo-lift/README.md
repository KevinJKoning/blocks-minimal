# Promotion lift

A retailer ran a promotion in 20 of its 40 stores for the last 8 of 52 weeks. How much did
the promotion raise weekly sales?

The data is synthetic, made by `data/generate.py` from known parameters (`data/truth.json`),
so the app can score its answer against the uplift the data was made with:

- `data/sales.csv.gz`: weekly sales in dollars, for every store and week, with whether the
  store was promoted;
- `data/truth.json`: the true uplift, and every parameter the sales were drawn from.

`panel` puts each store's sales before and after the promotion side by side. `estimate` is
the one judgment call, written two ways: how the lift is measured from those stores
(`nodes/estimate/`). `score` compares the estimate with the truth.
