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

To (re)download the data from Kaggle:

```sh
curl -L -o olist.zip https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce
unzip -o olist.zip -d data/raw
```

## Development

```sh
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run python -m unittest discover -s tests
```
