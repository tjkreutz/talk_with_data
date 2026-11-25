from duckdb import DuckDBPyConnection
from streamlit import cache_resource, chat_input, code, dataframe

from talk_with_data.database import create_connection
from talk_with_data.execution import run_query
from talk_with_data.generation import create_client, generate_sql
from talk_with_data.schema import describe_schema

PLACEHOLDER = "Ask a question about Olist orders and reviews"


def main() -> None:
    question = chat_input(PLACEHOLDER)

    if not question:
        return

    connection = _get_connection()
    sql = generate_sql(create_client(), question, describe_schema(connection))
    code(sql, language="sql")
    dataframe(run_query(connection, sql))


@cache_resource
def _get_connection() -> DuckDBPyConnection:
    return create_connection()


if __name__ == "__main__":
    main()
