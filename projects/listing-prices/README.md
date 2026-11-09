# Listing prices per square metre

From a year of messy property listings, what is the typical price per square metre in each
of 30 neighbourhoods?

The listings are synthetic, made by `data/generate.py` from known true prices
(`data/truth.json`), so the app can show how close it gets. Some neighbourhoods have only a
handful of listings, some listings carry a price or an area off by a factor of 10, some have
no area, and some are reposts of another listing.

`clean` reads the listings and sets aside what cannot be priced: a listing with no area, and a
repost. Three steps are judgment calls, so each is a fork, written every way worth defending:
which listings are too wrong to price with (`screen`), what a neighbourhood's typical value is
(`estimate`), and how much a neighbourhood with few listings should lean on the city as a whole
(`pooling`). `score` sets each neighbourhood's estimate against the truth. The answer is the
typical error across the 30 neighbourhoods, on this path and on every other.
