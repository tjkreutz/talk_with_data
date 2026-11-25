import logging
from collections.abc import Iterator
from dataclasses import dataclass

from duckdb import DuckDBPyConnection
from openai import OpenAI

from talk_with_data.execution import try_query
from talk_with_data.text_to_sql import generate_sql
from talk_with_data.writer import write_answer

LOGGER = logging.getLogger(__name__)
FAILURE = (
    "I could not run that query. I only know about orders and reviews, "
    "so the question may need data I do not have."
)


@dataclass(frozen=True)
class Answer:
    sql: str
    rows: list[tuple[object, ...]] | None = None
    text: str = ""
    error: str | None = None


def answer_question(
    connection: DuckDBPyConnection, client: OpenAI, schema: str, question: str
) -> Answer:
    *_, answer = stream_answer(connection, client, schema, question)

    return answer


def stream_answer(
    connection: DuckDBPyConnection, client: OpenAI, schema: str, question: str
) -> Iterator[Answer]:
    sql = generate_sql(client, question, schema)

    yield Answer(sql=sql)

    result = try_query(connection, sql)

    if result.error is not None:
        LOGGER.info("Query failed: %s", result.error)

        yield Answer(sql=sql, rows=[], text=FAILURE, error=result.error)

        return

    yield Answer(sql=sql, rows=result.rows)

    text = ""

    for piece in write_answer(client, question, sql, result.rows):
        text += piece

        yield Answer(sql=sql, rows=result.rows, text=text.strip())
