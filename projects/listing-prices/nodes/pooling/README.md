# How much should a neighbourhood with few listings lean on the city?

A neighbourhood with five listings has a noisy estimate, and a surviving error moves it a lot.
`own` takes each neighbourhood's estimate as it stands. `shrunk` blends it with the city's
median, with weight n / (n + `prior_listings`) on the neighbourhood, so a neighbourhood with many
listings keeps its own value and one with few is pulled toward the city. What bears on it is how
much neighbourhoods truly differ from one another, against how noisy a neighbourhood's own
estimate is, and that sets the right `prior_listings`: where the differences are large, as here,
it is small.

At the default of 10, `shrunk` roughly doubles the typical error in the sparse neighbourhoods
(about 2% becomes about 4%), so it is worse than `own`. Only near 0.5 does it stop hurting, and
there it moves the answer by under a tenth of a point. I would choose `own`: the city is a poor
place to lean on when neighbourhoods differ by about a third either way, and the `shrunk` option
would only earn its place on a city where they do not.
