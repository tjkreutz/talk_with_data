# Decisions

## Raw data

We dropped `olist_geolocation_dataset.csv`. It maps zip-code prefixes to
coordinates, with about 1M mostly duplicate rows. It would only matter for
exact maps, and `customer_state` and `customer_city` already cover location
questions. Without it the raw data shrinks from 120 MB to 62 MB, which is small
enough to keep in git.
