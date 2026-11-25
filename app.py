import logging

from duckdb import DuckDBPyConnection, Error
from streamlit import (
    cache_resource,
    caption,
    chat_input,
    code,
    dataframe,
    markdown,
    warning,
)

from talk_with_data.database import create_connection
from talk_with_data.execution import run_query
from talk_with_data.schema import describe_schema
from talk_with_data.text_to_sql import create_client, generate_sql
from talk_with_data.writer import write_answer

LOGGER = logging.getLogger(__name__)
PLACEHOLDER = "Ask a question about Olist orders and reviews"
FAILURE = (
    "I could not run that query. The app only knows about orders and reviews, "
    "so the question may need data it does not have."
)


def main() -> None:
    question = chat_input(PLACEHOLDER)

    if not question:
        return

    connection = _get_connection()
    client = create_client()
    sql = generate_sql(client, question, describe_schema(connection))

    try:
        rows = run_query(connection, sql)
    except (Error, ValueError) as failure:
        LOGGER.warning("Query failed: %s", failure)
        warning(FAILURE)
        code(sql, language="sql")
        caption(str(failure))

        return

    markdown(write_answer(client, question, sql, rows))
    code(sql, language="sql")
    dataframe(rows)


@cache_resource
def _get_connection() -> DuckDBPyConnection:
    return create_connection()


if __name__ == "__main__":
    main()
