from duckdb import DuckDBPyConnection
from streamlit import cache_resource, chat_input, empty
from streamlit.delta_generator import DeltaGenerator

from talk_with_data.answer import Answer, stream_answer
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
    slots = (empty(), empty(), empty())

    for answer in stream_answer(connection, create_client(), schema, question):
        _show(answer, *slots)


def _show(
    answer: Answer, sql: DeltaGenerator, result: DeltaGenerator, text: DeltaGenerator
) -> None:
    sql.code(answer.sql, language="sql")

    if answer.error is not None:
        result.caption(answer.error)
        text.warning(answer.text)
    elif answer.rows is not None:
        result.dataframe(answer.rows)

    if answer.error is None and answer.text:
        text.markdown(answer.text)


@cache_resource
def _get_connection() -> DuckDBPyConnection:
    return create_connection()


if __name__ == "__main__":
    main()
