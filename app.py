from duckdb import DuckDBPyConnection
from streamlit import cache_resource, chat_input, code, dataframe, markdown

from talk_with_data.database import create_connection
from talk_with_data.execution import run_query
from talk_with_data.schema import describe_schema
from talk_with_data.text_to_sql import create_client, generate_sql
from talk_with_data.writer import write_answer

PLACEHOLDER = "Ask a question about Olist orders and reviews"


def main() -> None:
    question = chat_input(PLACEHOLDER)

    if not question:
        return

    connection = _get_connection()
    client = create_client()
    sql = generate_sql(client, question, describe_schema(connection))
    rows = run_query(connection, sql)
    markdown(write_answer(client, question, sql, rows))
    code(sql, language="sql")
    dataframe(rows)


@cache_resource
def _get_connection() -> DuckDBPyConnection:
    return create_connection()


if __name__ == "__main__":
    main()
