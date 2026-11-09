# How much did the promotion raise weekly sales?

A retailer ran a promotion in 20 of its 40 stores for the last 8 of 52 weeks. How much did it
raise weekly sales in those stores?

The data is synthetic, made by `data/generate.py` from a known uplift (`data/truth.json`, 10%) so
the app can show how close it gets:

- `data/sales.csv`: 40 stores by 52 weeks, one row per store and week, with the store's size, its
  promotion flag and its weekly sales. The treated stores are the bigger ones, with a seasonal
  swing a third larger than the untreated ones, and twelve store-weeks are outliers.

`prepare` reads the panel and shows the two groups' average sales week by week: the promotion
weeks are the year's peak, so the gap between the groups is not the promotion alone. `clean`
decides what to do with the outlier store-weeks, a judgment call with three options. `estimate`
says what the treated stores would have sold without the promotion, another, with three options:
before and after in the treated stores alone, a difference in differences, and a comparison scaled
to the untreated stores before the promotion. `recovery` scores the estimate against the truth.

The answer is the uplift in weekly sales, as a share, marked on `estimate`. Both forks move it,
so the overview shows how far each one can take it. Neither fork is decided (`choices.json` is
empty): a run takes the first option by name, which is not a recommendation.
