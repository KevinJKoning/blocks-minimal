# How should the promotion's lift be measured?

Both ways take each store's sales after the promotion over its sales before. They differ in
what the promoted stores' change is compared with.

`did` (difference-in-differences) sets it against the other stores' change over the same
weeks, so whatever moved every store (the season, the holidays, a shock in one week) cancels.
It is right only if the promoted stores would have moved as the others did without the
promotion. Here they grow a little faster and respond a little more to the holidays, so it
is biased, but by much less than the alternative.

`naive` takes the promoted stores' own before-and-after change as the lift. Its weeks after
the promotion are the holiday season, so the holidays and the season are counted as lift.
It is the option to beat: `did` earns its place only by how much closer it comes to the truth,
which `score` shows.

Left open: I would choose `did`, since the other stores are the only evidence of what
the promoted stores would have done without the promotion.
