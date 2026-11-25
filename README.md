# Talk With Your Data

Ask natural-language questions about the
[Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
dataset and get answers back.

## Setup

```sh
uv sync
uv run pre-commit install
```

## Development

```sh
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run python -m unittest discover -s tests
```
