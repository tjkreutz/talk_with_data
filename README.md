# Talk With Your Data

Ask natural-language questions about the
[Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
dataset and get answers back.

## Setup

```sh
uv sync
uv run pre-commit install
```

## Data

### Kaggle data

To (re)download the data from Kaggle:

```sh
curl -L -o olist.zip https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce
unzip -o olist.zip -d data/raw
```

### Review search

The review vectors are in `data/vectors/review_embeddings.parquet` and load as the
table `review_embeddings`.

## Configuration

App settings (model, prompt, paths, views, evaluation and statistics parameters) are in `talk_with_data/config.py`.

The LLM is reached through an OpenAI-compatible API (we use OpenRouter). Copy
`.env.example` to `.env` and fill in `LLM_API_KEY`.

## Chat

```sh
uv run streamlit run app.py
```

Opens a chat in the browser. Each reply shows a short written answer, the
generated SQL and the table it returns.

## Evaluation

```sh
uv run python evaluation.py
```

Runs the model on the dev questions (5 runs each) and appends a summary line
to `data/experiments.jsonl`.

## Development

```sh
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run python -m unittest discover -s tests
```
