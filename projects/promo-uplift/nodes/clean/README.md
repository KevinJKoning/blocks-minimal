# What should be done with the store-weeks the screen flags?

The screen flags a store-week whose sales sit far from what its store, its week and the promotion
predict. Those flags can be real sales (a bulk order, a local event) or data errors (a stock-out,
a bad feed), and the estimates depend on which. Keep leaves them as recorded; exclude drops them;
cap keeps each row but pulls its excess back to the flag's edge, so one spike cannot move a store.

I would choose cap. A flagged week may be real, so dropping it throws away a week that happened
(exclude), and keeping it lets a single spike pull the estimate (keep). The `estimate` fork shows
how far each of the three moves the uplift.
