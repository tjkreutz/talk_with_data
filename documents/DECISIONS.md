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

## Storage

We load the raw CSVs into an in-memory DuckDB database, one table per CSV named
after its file (`olist_orders_dataset.csv` becomes `orders`). DuckDB reads CSVs
directly and runs analytical SQL fast, and there is no database file to keep in
sync with `data/raw/`. Loading all 8 files takes under half a second. We rely on
DuckDB's type detection: timestamps become `TIMESTAMP`, and zip prefixes stay
text, so their leading zeros survive.

## Baseline: text-to-SQL with a bare schema

The baseline is one LLM call per question. The model gets the schema and the
question and returns one DuckDB query. It is the simplest thing that works, so
every later improvement can be measured against it on dev.

- **Bare schema, no help.** The prompt holds only the `CREATE TABLE` text of
  `orders`, `order_reviews` and `customers`, generated from the live DuckDB
  tables so it cannot drift from the data. There are no column descriptions,
  no sample rows, no few-shot examples and no warnings about the known traps.
  Each of those is a separate experiment later, so we can attribute a gain to
  it. The traps (customer_id vs customer_unique_id, date-only estimates,
  accented city names) are expected to be where the baseline fails.
- **Three tables, not eight.** The loader creates all 8 tables, but the model
  only sees the assignment's three core ones, which is all the 300 questions
  need. Fewer tables means fewer wrong joins and a fair baseline.
- **SQL only.** The baseline returns SQL and nothing else. The plain-language
  explanation of the result is a second call, kept out of the metric.
- **Haiku 5.5 first, through OpenRouter.** Haiku is cheap and fast (1–2 s per
  question in a first check), and starting small shows how much better prompting
  buys before we pay for a bigger model. OpenRouter speaks the OpenAI API, so we
  use the `openai` SDK, with the endpoint and key in `.env`.
