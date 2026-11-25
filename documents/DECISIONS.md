# Decisions

## Raw data

We dropped `olist_geolocation_dataset.csv`. It maps zip-code prefixes to
coordinates, with about 1M mostly duplicate rows. It would only matter for
exact maps, and `customer_state` and `customer_city` already cover location
questions. Without it the raw data shrinks from 120 MB to 62 MB, which is small
enough to keep in git.

## Question set

We evaluate on 300 questions: 100 train, 100 dev, 100 test, in
`data/questions/`. Train is for few-shot examples and prompt ideas, dev for
tuning, and test is run rarely to report the final numbers.

- **Deterministic metric.** Every question has a gold SQL query. We run the
  app's SQL and the gold SQL on the same data and compare the results, so the
  score is a plain match rate. Questions without one correct result (ambiguous,
  unanswerable, decline) are left out for now.
- **Split by template.** Questions come in groups of 5 variants of one template
  (the `template` field). All variants of a template land in the same split, so
  test measures questions the app has never seen in any form. A random split
  would put near-twins in train and test and inflate the test score.
- **Same mix in every split:** 60 answerable, 25 trap-aware and 15 noisy
  phrasing. Trap-aware questions only come out right if the SQL avoids a known
  pitfall (customer_id vs customer_unique_id, comparing the date-only estimate
  with a timestamp, incomplete edge months, accented city names, zip codes with
  leading zeros). Noisy questions ask for the same kind of answer with typos,
  Portuguese or German, shouting, slang, a false premise or very terse wording.
- **Scope:** only `orders`, `order_reviews` and `customers`.
- **Sources:** the Kaggle data card (its "Inspiration" topics), the Kaggle
  discussion board (customer_id vs customer_unique_id, the 24 November 2017
  spike, review duplicates, the data being a sample) and our own checks of the
  CSVs.
