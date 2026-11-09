# Price per square metre by neighbourhood

From a year of messy property listings, what is the typical price per square metre in each
of 30 neighbourhoods?

The data is synthetic, made by `data/generate.py` from known true prices (`data/truth.json`)
so the app can show how close it gets:

- `data/listings.csv`: 1,546 listings from a year of portal scrapes, in 30 neighbourhoods.
  Some neighbourhoods have only three to six listings, a few are repeated, 76 have no floor
  area, and some carry a data-entry error of a factor of 10 in the price or the area.
- `data/truth.json`: the true price per square metre of each neighbourhood.

`clean` drops the repeats and the listings with no area, and gives each listing a price per
square metre. `outliers` deals with the listings that are off by a factor of 10 (drop them,
correct them, or keep them). `estimate` takes each neighbourhood's typical price per square
metre: its median, or that median pulled toward the city's when it has few listings. Both
are judgment calls, so each is a fork. `recovery` scores the estimates against the truth.

The answer is the typical error of a neighbourhood's estimate against its true price per
square metre, on this path and on every other.
