from duckdb import DuckDBPyConnection
from streamlit import (
    cache_resource,
    caption,
    chat_input,
    code,
    dataframe,
    markdown,
    warning,
)

from talk_with_data.answer import answer_question
from talk_with_data.database import create_connection
from talk_with_data.schema import describe_schema
from talk_with_data.text_to_sql import create_client

PLACEHOLDER = "Ask a question about Olist orders and reviews"


def main() -> None:
    question = chat_input(PLACEHOLDER)

    if not question:
        return

    connection = _get_connection()
    schema = describe_schema(connection)
    answer = answer_question(connection, create_client(), schema, question)

    if answer.error is not None:
        warning(answer.text)
        code(answer.sql, language="sql")
        caption(answer.error)

        return

    markdown(answer.text)
    code(answer.sql, language="sql")
    dataframe(answer.rows)


@cache_resource
def _get_connection() -> DuckDBPyConnection:
    return create_connection()


if __name__ == "__main__":
    main()
