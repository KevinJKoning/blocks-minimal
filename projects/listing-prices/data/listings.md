The year's property listings, as a **CSV** with one row per listing:

| column | means |
|---|---|
| `listing_id` | an identifier, unique within the file (a repost gets a new one) |
| `neighbourhood` | the neighbourhood's code, one of 30 |
| `listed` | the month the listing was posted, `YYYY-MM` |
| `price` | the asking price, in currency units |
| `area_m2` | the floor area in square metres; blank where the listing gives none |

Messy the way an agency's export is: some listings have a price or an area off by a factor
of 10, some are reposts of another listing (the same neighbourhood, month, price and area),
and some have no area.
