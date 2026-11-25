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

## Metric: execution accuracy

A generated query is correct when it returns the same result as the gold SQL on
the same data. We compare results, not SQL text, because two different queries
can be equally right (`EXTRACT(YEAR FROM x)` and `year(x)`), and text matching
would punish that. The comparison is `results_match` in
`talk_with_data/comparison.py`, a pure function over two lists of rows.

- **Column names are ignored.** Aliases are arbitrary. The number of columns
  must match, so an extra column counts as wrong.
- **Row order is ignored, unless the gold SQL has an `ORDER BY`.** Then order
  must match. A gold query with `ORDER BY` inside a window function also counts
  as ordered, which only matters for multi-row results.
- **Numbers are rounded to the precision of the gold column.** Gold queries
  round (12.6), the model usually does not (12.557), so the model's value is
  rounded to the gold's number of decimals. A gold column of whole numbers
  needs an exact match, so 7.4 does not pass for 7.
- **Days are whole days.** Gold queries measure day differences with
  `date_diff('day', start, end)`, which counts calendar-day boundaries crossed
  (a purchase at 23:00 and a delivery at 01:00 the next day is 1 day). We first
  averaged fractional days (`epoch` differences), but the model usually counts
  whole days and both are fair readings of "days", so correct answers scored as
  wrong. Averages and medians are rounded to one decimal. Hours are unchanged
  (`approval_hours_month`).

Known limits, found by checking 20 dev questions by hand:

- **Thresholds stay ambiguous.** "Took more than 45 days" can mean more than 45
  whole days or more than 45 days of elapsed time. The model uses both
  readings, sometimes within one template, and only the first matches our gold.
- **Derived labels.** A query that returns labels such as `late` and `on time`
  only matches if the model picks the same strings. We accept that for now.
- **Coincidental matches.** A wrong query can match by chance, mostly where the
  gold answer is 0 or a single row.

## Evaluation protocol

`evaluation.py` runs an experiment on one split (dev for now) and appends one
summary line to `data/experiments.jsonl`. The model has no temperature setting,
so every question is asked 5 times, and all numbers are averaged over those
runs. SQL is generated concurrently, then executed one query at a time. Only a
single `SELECT` is accepted, so a model that writes `DROP TABLE` cannot corrupt
the rest of the run.

Each line in `experiments.jsonl` carries what identifies the experiment and its
results:

- **Identity:** `id` (the label plus the start time), `experiment` (the label), `timestamp`, `git_commit` (with
  `+dirty` if there were uncommitted changes), `model`, `prompt_hash` (a hash
  of the exact system prompt including the schema, so a prompt change always
  shows), `tables` and `split`.
- **Size:** `questions` and `runs`.
- **Results:** `accuracy` and `accuracy_std` (the standard deviation of the
  per-run accuracies, which is the model's own run-to-run noise),
  `accuracy_ci95`, `outcomes`, `consistency` and `template_accuracy`.
- **Outcomes** are `correct`, `wrong` (a different result), `empty` (no rows
  returned) and `error` (invalid SQL or not a single `SELECT`).
- **Consistency** counts questions that were right in all runs, in some runs,
  or in none. Questions that flip between runs are the ones where the model is
  unsure.

Every attempt is also written to `data/runs/<id>.jsonl`: the question, the
generated SQL, the outcome, and the first rows of the model's result next to
the gold result. These files are for error analysis, so they are gitignored and
stay local. The `id` links a line in `experiments.jsonl` to its run file.

There are two separate sources of uncertainty, and the numbers keep them apart.
The 5 runs measure how much the model varies on the same question
(`accuracy_std`). `accuracy_ci95` is a bootstrap that resamples the templates
with replacement, because the 5 variants of a template are not independent and
a split only has 20 templates. It measures how much the score depends on which
questions we happened to pick, and it is much wider than the run noise. To
compare two experiments, compare them template by template on the same dev
questions, not by whether their intervals overlap.

Baseline (bare schema, Haiku 5.5, dev), measured twice: accuracy 0.740 and
0.742, run-to-run std 0.022 and 0.020. The second run has a 95% interval of 0.56
to 0.89. There were no SQL errors and no empty results, every miss was a wrong
answer. Four templates scored 0 in every run: the date-only estimate
(`late_vs_ontime_state`, `late_score_gap_month`), accented city names
(`avg_score_accented_city`, the model returns NULL for Florianópolis) and
returning customers (`returning_orders_month`). These are the traps we expected.

The partial misses show the limits of the metric as much as of the model:

- **Whole against fractional days.** On some runs the model averages
  `EXTRACT(EPOCH ...) / 86400.0` where the gold counts whole days
  (`estimated_days_state`, `carrier_days_state`, `median_delivery_days_state`).
- **"More than N days"** is read as elapsed time in some runs
  (`deliveries_over_days`).
- **Month labels.** The model groups with `DATE_TRUNC('month', ...)`, which gives
  timestamps, and the gold has `'2018-01'` strings (`monthly_orders_state_year`).
- **Derived labels and column order.** The model writes `Late` and `On-time`
  where the gold has `late` and `on time`, in a different column order
  (`late_vs_ontime_state`).
- **Ties.** A top-6 list that is cut off among equal counts, and ordered
  comparison breaking on ties inside the list (`top_cities_state`).
- **How many to return.** "When do customers order the most?" gets a top 5
  where the gold has one hour (`busiest_hour`).
