The calibration rig's raw readings, as a **Parquet** file with one row per reading and two
numeric columns:

| column | means |
|---|---|
| `reading` | the sensor's raw output |
| `reference` | the reference instrument's value at the same moment |

Missing values are allowed (those rows are dropped); other columns are ignored.
