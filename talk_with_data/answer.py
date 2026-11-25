import logging
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
    text: str
    sql: str
    rows: list[tuple[object, ...]]
    error: str | None = None


def answer_question(
    connection: DuckDBPyConnection, client: OpenAI, schema: str, question: str
) -> Answer:
    sql = generate_sql(client, question, schema)
    result = try_query(connection, sql)

    if result.error is not None:
        LOGGER.info("Query failed: %s", result.error)

        return Answer(text=FAILURE, sql=sql, rows=[], error=result.error)

    text = write_answer(client, question, sql, result.rows)

    return Answer(text=text, sql=sql, rows=result.rows)
