# Sensor calibration

Which calibration curve best maps a low-cost sensor's raw reading to the reference
instrument on held-out data, without extrapolating badly?

Raw readings (`data/measurements.parquet`, 400 paired readings from the calibration rig)
are cleaned (dropouts removed, connector spikes screened with a robust residual cut),
expanded into standardized polynomial features and fitted with closed-form ridge
regression. The exploration settled on a cubic (degree 3) with alpha 0.1: higher degrees
improved held-out RMSE by under 5 % and extrapolate badly past the calibrated range
(readings 0–10). `calibrated` delivers every reading with its calibrated value (CSV) and
the curve's equation (Markdown).
