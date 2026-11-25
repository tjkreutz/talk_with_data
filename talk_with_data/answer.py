import logging
from collections.abc import Sequence

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


def answer_question(
    connection: DuckDBPyConnection,
    client: OpenAI,
    schema: str,
    question: str,
    history: Sequence[tuple[str, str]] = (),
) -> str:
    sql = generate_sql(client, question, schema, history=history)
    result = try_query(connection, sql)

    if result.error is not None:
        LOGGER.info("Query failed: %s", result.error)

        return FAILURE

    return write_answer(client, question, sql, result.rows)
