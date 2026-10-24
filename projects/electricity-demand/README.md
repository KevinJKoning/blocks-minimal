# Electricity demand forecast

How much electricity will the utility need each month over the next year or two, and how
sure can it be?

The data is synthetic, made by `data/generate.py`: `data/demand.csv` holds ten years of
monthly demand (January 2015 to December 2024, in GWh) with steady load growth, a winter
heating peak, a smaller summer cooling peak and noise.

`history` reads the series. `fit` fits a simple seasonal model by least squares, a linear
trend plus one level per position in a season of `season_length` months, and shows it
against the history. `forecast` extends it `horizon` months ahead with an 80% prediction
interval and delivers the forecast as a CSV.
