# What would the treated stores have sold without the promotion?

The promotion weeks are the year's peak, and the treated stores swing more with the season than the
untreated ones do. So comparing the treated stores with themselves counts the season as promotion
(naive), and a difference in differences, which shares the season across both groups, still misses
where the two groups swing differently (did). Scaling the untreated stores to the treated ones
before the promotion carries that swing into the promotion weeks (scaled).

I would choose scaled. Its only assumption is that the treated stores' sales track the untreated
stores' with a fixed sensitivity to the season, which the weeks before the promotion can check; did
assumes the two groups share the season outright, and the data says they do not.
