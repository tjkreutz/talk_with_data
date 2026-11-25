# Talk With Your Data

Ask questions in plain language about the
[Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
dataset (orders, customers and reviews) and get a short written answer back,
with the SQL that produced it.

## Quick start

You need [uv](https://docs.astral.sh/uv/) and an [OpenRouter](https://openrouter.ai)
API key. One key covers all the models the app uses.

```sh
uv sync
cp .env.example .env
```

Then put your key in `.env` as `LLM_API_KEY`. The data is already in the
repository, so there is nothing to download.

### Terminal chat

```sh
uv run python main.py
```

Asks for a question, prints the written answer, and repeats until you enter an
empty line. It prints only the answer and does not remember earlier questions.

### Browser chat

```sh
uv run streamlit run app.py
```

Each reply shows the generated SQL, the result table and a written answer, and
the conversation is remembered, so follow-ups work.

## What you can ask

- `How many orders were delivered in 2017?` then `And in 2018?`
- `What share of orders were canceled?`
- `How many reviews gave 1 star?`
- `What do customers say about late deliveries?` (searches the review texts)
- `Was sagen Kunden über den Kundenservice?` (any language works)

The app only knows orders, customers and reviews. For anything else it says so
instead of guessing.

## How it works

1. **Text to SQL.** Gemini 3.5 Flash Lite writes a DuckDB query. It sees the
   columns of two views, `order_facts` and `review_facts`, a short glossary and
   a few examples (`data/prompts/text_to_sql_prompt.txt`), and in the browser
   chat the last five questions with their SQL. For free-text questions about
   reviews it can call a semantic search over the review texts first.
2. **Run.** The query runs on an in-memory DuckDB database built from the CSVs
   at start-up. Only a single `SELECT` is accepted.
3. **Write.** Llama 3.1 8B turns the question, SQL and result into one to three
   sentences.

The views, the prompt and the reasons behind each choice are in
[`documents/DECISIONS.md`](documents/DECISIONS.md).

## Layout

| Path | What is in it |
|---|---|
| `main.py`, `app.py`, `evaluation.py` | Entry points: terminal chat, browser chat, evaluation |
| `talk_with_data/` | All the logic. `answer.py` is the pipeline; `config.py` holds every setting |
| `data/raw/` | The Olist CSVs (without the geolocation file) |
| `data/sql/`, `data/prompts/` | The view definitions, queries and prompts |
| `data/vectors/` | Review embeddings for the semantic search |
| `data/questions/` | 300 evaluation questions with gold SQL: train, dev, test |
| `data/experiments.jsonl` | One line per evaluation run |
| `tests/` | Unit tests |

## Configuration

Models, prompts, paths, history length and the evaluation settings are
constants in `talk_with_data/config.py`. The browser theme is in
`.streamlit/config.toml`. The LLM is reached through an OpenAI-compatible API,
set by `LLM_API_URL` and `LLM_API_KEY` in `.env`.

## Evaluation

```sh
uv run python evaluation.py
```

Runs the model on the dev questions, 5 times each, and appends a summary line
to `data/experiments.jsonl`. The split and the experiment name are `SPLIT` and
`EXPERIMENT` in `config.py`. Every attempt is also saved under `data/runs/`
(not committed) for error analysis.

A question counts as correct when its query returns the same result as the gold
query. Latest numbers:

| Split | Accuracy |
|---|---|
| Dev (used for tuning, so optimistic) | 0.94 |
| Test (95% interval 0.85 to 1.00) | 0.95 |

For comparison, the first baseline, a bare schema with Haiku, scored 0.74 on
dev. The questions do not cover review search or follow-ups yet, so those are
only checked by hand. See `documents/DECISIONS.md` for the metric and its
limits.

## Data

The CSVs are committed in `data/raw/`. We dropped the geolocation file, which
is large and not needed. To download them again:

```sh
curl -L -o olist.zip https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce
unzip -o olist.zip -d data/raw -x olist_geolocation_dataset.csv
```

The review embeddings in `data/vectors/review_embeddings.parquet` were made
once with `mongodb/voyage-4-lite` at 256 dimensions and are committed too.
Changing the embedding model means regenerating that file.

## Development

```sh
uv run pre-commit install
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run python -m unittest
```
