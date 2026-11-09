# Which listings are too wrong to price with?

A listing with a price or an area off by a factor of 10 has a price per square metre ten
times, or a tenth of, what it should be, and an average of its neighbourhood moves with it.
The options differ in what they measure a listing against: nothing (`none`), the city as a whole
(`city_ratio`), or its own neighbourhood (`neighbourhood_ratio`). Each drops a listing that is
more than `factor` times away. What bears on it is how far the answer moves with the choice,
and whether a neighbourhood with few listings can tell its own errors from its real values.

On this data the choice matters only if the estimate is a mean: with `none` and a mean the
typical error is about 30%, and with either screen it is about 2%. With a median the three are
within a fraction of a point of one another. I would choose `city_ratio`: its yardstick is the
city's median, which does not come from the handful of listings in a sparse neighbourhood, so a
sparse neighbourhood's own errors cannot hide in it.
