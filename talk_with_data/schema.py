from collections.abc import Sequence

from duckdb import DuckDBPyConnection

from talk_with_data.config import VIEWS
from talk_with_data.utils import load_sql


def describe_schema(
    connection: DuckDBPyConnection, views: Sequence[str] = VIEWS
) -> str:
    statements = (_get_create_statement(connection, view) for view in views)

    return "\n".join(statements)


def _get_create_statement(connection: DuckDBPyConnection, view: str) -> str:
    rows = connection.execute(load_sql("view_columns"), [view]).fetchall()

    if not rows:
        raise ValueError(f"Unknown view: {view}")

    columns = ", ".join(f"{name} {data_type}" for name, data_type in rows)

    return f"CREATE VIEW {view}({columns});"
