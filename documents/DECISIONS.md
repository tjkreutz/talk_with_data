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
- **Row order must match.** Every multi-row gold query has an `ORDER BY` (25 of
  300 questions, none without), so there is nothing to gain from an
  order-insensitive comparison. We had one at first, and removed it because it
  never ran on real data. If we ever add a multi-row question without an
  `ORDER BY`, we need to bring it back.
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

## Model choice: Haiku and Flash Lite, not Sonnet

We compared three models on dev with the bare schema and the same prompt, 5 runs
per question (`model_choice` in `experiments.jsonl`):

| Model | Accuracy | Median / p95 latency | Run time | Price per 1M tokens (in / out) |
|---|---|---|---|---|
| Haiku 5.5 | 0.724 (and 0.742 in `baseline`) | 1.36 s / 3.04 s | 98 s | $0.10 / $0.50 |
| Gemini 3.5 Flash Lite | 0.660 | 0.90 s / 1.47 s | 62 s | $0.30 / $2.50 |
| Claude Sonnet 5.5 | 0.656 | 1.42 s / 3.33 s | 108 s | $2 / $10 |

The run-to-run standard deviation is between 0.01 and 0.02 for all three. We chose these
three after a short latency probe (5 questions each). The newer Gemini 3.8 and 4
models think about a thousand tokens before answering by default, which made
them 7 to 11 seconds per question, so we left them out.

**Decision: we leave Sonnet after these model experiments.** It was no more
accurate than Haiku on the strict metric (0.656 against 0.72 to 0.74), it has
the longest tail latency and the longest run time, and it costs 20 times as much
per token. It did better on the accented-city trap (1.00 against 0.00 to 0.04
for Haiku), but it lost more on templates where the gold fixes a convention, such as
whole against fractional days and month labels. The bigger model did not buy
accuracy here. Every experiment after this one uses only Haiku 5.5, for
accuracy, and Gemini 3.5 Flash Lite, for speed. Sonnet was never run with the
views, so we make no claim about it beyond this comparison.

## Semantic views: order_facts and review_facts

The error analysis of the baseline showed systematic gaps, not noise: the raw
tables carry traps (`customer_id` is per order, the estimated delivery date has
no time of day, durations and months must be derived). Instead of adding hints
to the prompt, we put the semantics in the data. `create_connection` builds two
DuckDB views right after the CSVs load, and the model sees only these two views
(column names and types, not their definitions). The raw tables stay in the
database, so the gold SQL and the eval are unchanged.

- **`order_facts`**, one row per order: orders joined with the customer
  columns, `customer_unique_id` instead of `customer_id`, calendar columns
  (`purchase_month` as `'YYYY-MM'`, year, quarter, weekday, hour), date-typed
  `delivered_date` and `estimated_delivery_date`, whole-day durations
  (`days_to_deliver`, `days_estimated`, `days_carrier_to_customer`), `is_late`
  (date-level comparison, only for delivered orders) and `customer_order_number`
  (the n-th order of a person, ties broken by `order_id`).
- **`review_facts`**, one row per review: the review columns, `has_comment`,
  `days_to_answer`, and every `order_facts` column, so review questions need no
  join. It has exactly as many rows as `order_reviews` (99,224).
- **Rule for adding a column:** it must be standard modelling practice, something
  a data engineer would add without our questions (typed grain, calendar
  columns, lifecycle durations, entity keys, status flags). No column is named
  after a question, and the prompt did not change.
- **A view must keep every raw attribute that questions can use.** Our first
  version left out `customer_zip_code_prefix`, and the zip questions fell from
  1.0 to 0.0 accuracy. Removing an attribute silently removes a capability.

Results on dev (strict metric, 5 runs per question, same prompt):

| Model | Raw schema | Views | Median / p95 latency with views |
|---|---|---|---|
| Haiku 5.5 | 0.742 and 0.724 | 0.870 | 1.30 s / 2.53 s |
| Gemini 3.5 Flash Lite | 0.660 | 0.878 | 0.80 s / 1.14 s |

With the views the cheap fast model catches up with Haiku (0.878 against
0.870, within the run noise) at about 0.8 s, so once the semantics are in the
data the choice of model matters much less. The
conventions in the views (whole days, `'YYYY-MM'`, date-level lateness) are
choices that match the gold's, which makes part of the comparison circular. We
say so rather than hide it.

What still fails on dev is mostly about output conventions:

- **Label text and column order** in `late_vs_ontime_state` (25 of 500 attempts
  for each model).
- **How many rows or columns to return.** Top-N against top 1
  (`busiest_hour`, 15 of 500 for Haiku and 8 for Flash Lite), and extra columns
  returned (`late_score_gap_month`, 3 and 2).
- **Month recomputed.** Haiku ignores `purchase_month` and groups by
  `DATE_TRUNC('month', ...)`, 14 of 500 attempts. A column existing does not make
  the model use it.
- **Accented city names** still trip Haiku a little (6 of 500 attempts).
- **Nested queries.** Flash Lite loses 14 of 500 attempts on `new_customers_month`,
  13 of them SQL errors from referencing a column outside its subquery.

## Semantic layer in the prompt: glossary and few-shot examples

Views fix the data model, but the model still lacked conventions (percent
against fraction, lowercase city names, how many rows to return). We tried a
short glossary, six few-shot examples, and both, on dev with Flash Lite and 5
runs (`semantic_layer` in `experiments.jsonl`). The base prompt is the
`introduce_views` line, so we did not run it again.

| Prompt | Hash | Accuracy |
|---|---|---|
| Base (views only) | `d4742522` | 0.878 |
| Glossary | `32c5c4e5` | 0.908 |
| Few-shot | `68cfb07f` | 0.888 |
| **Glossary and few-shot** | `6c593faf` | **0.936** |

**Decision: keep both.** They fix different things. The glossary fixes the
conventions (new customers, approval hours) and few-shot fixes the answer shape
(busiest hour). Each alone also breaks something (glossary alone: `busiest_hour`,
few-shot alone: `returning_orders_month`), and together nothing gets worse. The
latency is unchanged (about 0.8 s median) and the prompt is about 380 words,
kept in `data/prompts/text_to_sql_prompt.txt`. The default model is now Flash Lite.

- The examples are six train questions. Their SQL is written for the views and
  returns exactly the train gold result.
- It took three rounds of trial and error on dev, so the dev score is
  optimistic. Test is still untouched. Two glossary lines backfired on the way:
  "answer with just the requested value" dropped the measure from rankings, and
  "city names are lowercase" made the model lowercase state codes.
- Still failing: label text and column order in `late_vs_ontime_state`, and
  `carrier_days_state`, where the model's own rounding to 2 decimals meets our
  rounding to 1.

## Semantic search over reviews, as a tool

Free-text review questions cannot be answered with the views, so the model can
call `search_reviews(query)`, which returns the 10 most similar reviews as JSON.

- **Model: hosted `mongodb/voyage-4-lite`, cut to 256 dimensions.** It is the
  only small multilingual embedding model on OpenRouter, and it found the right
  Portuguese review for 7 of 7 test queries (English-only MiniLM: 1 of 7).
- **The vectors are a committed data file, like the raw CSVs.** The 42,697
  reviews with a title or message are embedded once into
  `data/vectors/review_embeddings.parquet` (48 MB, under GitHub's 50 MB warning),
  and `create_connection` loads it as a table. There is no build script, so
  changing the model or dimensions means regenerating the file by hand.
- **Tools are optional in `generate_sql(..., tools=...)`.** We use the OpenAI
  SDK's own classes and no tool class of our own: a tool is a pydantic model for
  its arguments, which `pydantic_function_tool` turns into the definition and
  `parse()` turns the model's arguments back into, plus a function registered
  in `make_tools`.
- **`answer_question` passes the tools,** so the terminal chat can search.
  Experiments (`run_experiment`) still run without them, so the 300 gold
  questions and the recorded numbers are unaffected; the prompt hash changed
  with the one glossary line that tells the model when to search.
- **Seen in a hand test of 4 review questions and 4 plain ones** (not an
  evaluation): with only the tool's description, the model searched up to three
  times, then ignored the ids and fell back to `LIKE` or an aggregate over
  `review_facts`, or selected `review_text`, a column the view does not have.
  Telling it to search once, then select `review_comment_message` for the
  returned ids and never to search text with `LIKE`, fixed all four: one search
  each, ten reviews back, about 3 s. Plain questions never searched and took
  1 to 3 s.
- **The writer was the weak step on review answers,** so its prompt got rules
  for them. Before: it counted 9 reviews where 10 came back, answered an
  English question in Portuguese, dumped ten order ids, and wrote "63%" for the
  result 0.63. After, on the same questions: it describes the common themes and
  score range, translates quotes into the language of the question (German
  included), names at most three ids, and writes "0.63%". The percentage rule
  only worked once it had a worked example; a plain rule was ignored by the 8B
  model.
- **Still open:** the model sometimes aggregates over the ten search results
  ("90% of reviews are positive" about packaging), which is a statistic about
  ten reviews, not all of them. That is for the SQL prompt, not the writer.
  Twice it also searched twice despite "once".


## Writer: a small second model summarizes the answer

`write_answer(client, question, sql, rows)` in `writer.py` turns the question,
the SQL and its result (at most 20 rows) into one to three sentences. It
streams them chunk by chunk, and `app.py` shows the SQL, the table and then the
text as it forms. It uses a different, much cheaper model from the SQL step, set
in `config.py`.

- **Model: `meta-llama/llama-3.1-8b-instruct` at temperature 0.** We compared
  eight small models on five cases (a count, a percentage, a top 3, an empty
  result, Portuguese review text). Llama was the fastest (about 0.2 s, against
  1.7 s for Mistral Small 24B) and answered in the language of the question. At
  the default temperature it once invented a number, and at temperature 0 it
  invented none in 5 of 5 runs. Gemma 3, Ministral and Nova Micro were sloppier:
  wrong decimal formats, invented numbers, the wrong language.
- **The prompt is a file,** `data/prompts/writer_prompt.txt`. Not evaluated yet,
  so the writer is only checked by that small comparison.

## History awareness: follow-up questions

`generate_sql(..., history=...)` lets the text-to-SQL model resolve follow-ups
such as "and in 2018?". Each earlier turn goes in as a user message (the
question) and an assistant message (the SQL that answered it), ahead of the new
question.

- **Bounded to the last 5 turns** (`HISTORY_TURNS` in `config.py`).
- **Failed turns are left out,** so bad SQL is not repeated as an example.
- **Only the SQL step sees the history.** The writer sees the current SQL, which
  already carries the context.
- **Optional, off by default,** so the prompt, the eval and every recorded
  experiment are unchanged.

**Limitation: we never tested this in a structured way.** The eval set has only
single questions, so nothing measures follow-ups. All we have is ad hoc checking by hand: one
four-turn conversation that resolved correctly (2017, then 2018, then São Paulo,
then the review score for those), and one follow-up without history, which made
up a Niterói filter, probably copied from a few-shot example. The limit of 5
turns, leaving out failed turns, and not giving the writer the history are
guesses, not measured choices. Doing it properly would mean a set of multi-turn
questions with gold SQL for the last turn, run with and without history.
