What `data/generate.py` drew the sales from, as **JSON**. `uplift` is the true lift the app is
scored against: the mean, over the promoted stores, of the uplift each one was given (their
own uplifts are in `store_uplift`). The rest says how the sales were made: the holiday
response and the trend of the promoted stores, which the estimates have to cope with, and
how many outlier weeks were added. It exists only because the data is synthetic; with real
sales there is no truth to replace it with.
