# Windstorm territory rates

What should a homeowners windstorm policy cost in each of 300 coastal territories, when most
territories have too little experience to rate on their own?

The data is synthetic, made by `data/generate.py` from known parameters
(`data/truth.json`) so the app can show how close it gets:

- `data/policies.csv.gz`: 100,000 policies as points, with exposure (years), construction,
  roof age, deductible and windstorm claim counts;
- `data/territories.geojson`: 300 territory polygons with their terrain (urban, suburban,
  open), in metres on a local projection;
- `data/coast.geojson`: the coastline.

`join` places each policy in its territory and measures its distance inland: one dataset of
tabular and geospatial data. `wind` turns that distance into a physics offset, the relative
wind load from the inland decay of a hurricane's wind. `glm` fits a Poisson GLM of claim
frequency on the rating factors with that offset. `credibility` blends each territory's own
experience with the GLM (Bühlmann–Straub), and `rates` sets every territory's base rate.
`recovery` scores it all against the truth.
