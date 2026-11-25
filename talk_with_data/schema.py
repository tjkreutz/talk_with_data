from collections.abc import Sequence

from duckdb import DuckDBPyConnection

from talk_with_data.config import MODEL_TABLES
from talk_with_data.utils import load_sql


def describe_schema(
    connection: DuckDBPyConnection, tables: Sequence[str] = MODEL_TABLES
) -> str:
    statements = (_get_create_statement(connection, table) for table in tables)

    return "\n".join(statements)


def _get_create_statement(connection: DuckDBPyConnection, table: str) -> str:
    rows = connection.execute(load_sql("table_columns"), [table]).fetchall()

    if not rows:
        raise ValueError(f"Unknown table: {table}")

    kind = "VIEW" if rows[0][0] == "VIEW" else "TABLE"
    columns = ", ".join(f"{name} {data_type}" for _, name, data_type in rows)

    return f"CREATE {kind} {table}({columns});"
