import json
from collections.abc import Sequence

from duckdb import CatalogException, DuckDBPyConnection
from openai import OpenAI

from talk_with_data.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, SEARCH_RESULTS
from talk_with_data.utils import load_sql


def search_reviews_json(
    connection: DuckDBPyConnection, client: OpenAI, query: str
) -> str:
    return json.dumps(search_reviews(connection, client, query), ensure_ascii=False)


def search_reviews(
    connection: DuckDBPyConnection, client: OpenAI, query: str
) -> list[dict[str, object]]:
    if not query.strip():
        raise ValueError("The search term is empty")

    vector = _embed_query(client, query)

    try:
        relation = connection.execute(
            load_sql("search_reviews"), [vector, SEARCH_RESULTS]
        )
    except CatalogException as error:
        raise RuntimeError("The review vectors file is missing") from error

    return _to_dicts(relation.description, relation.fetchall())


def _embed_query(client: OpenAI, query: str) -> list[float]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL, input=[query], dimensions=EMBEDDING_DIMENSIONS
    )

    return response.data[0].embedding


def _to_dicts(
    description: Sequence[Sequence[object]], rows: Sequence[Sequence[object]]
) -> list[dict[str, object]]:
    names = [str(column[0]) for column in description]

    return [dict(zip(names, row, strict=True)) for row in rows]
