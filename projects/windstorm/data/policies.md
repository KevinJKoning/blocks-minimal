The policies, as a **gzipped CSV** (`.csv.gz`: a replacement takes this file's name, so it
must be gzipped too), one row per policy:

| column | means |
|---|---|
| `policy_id` | an identifier |
| `x`, `y` | the home's location, in the same projected metres as `territories` and `coast` |
| `exposure` | policy-years in force |
| `construction` | `frame`, `masonry` or `concrete` |
| `roof_age` | the roof's age in years |
| `deductible` | the deductible, in currency units |
| `claims` | the number of windstorm claims |
