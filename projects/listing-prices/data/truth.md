What `data/generate.py` drew the listings from, as **JSON**: `price_per_m2`, each
neighbourhood's true price per square metre, which the app scores its answer against. It
exists only because the data is synthetic; with real listings there is no truth to replace it
with, and the app's `score` node has nothing to compare with.
