from collections.abc import Sequence

from duckdb import DuckDBPyConnection

CORE_TABLES = ("orders", "order_reviews", "customers")


def describe_schema(
    connection: DuckDBPyConnection, tables: Sequence[str] = CORE_TABLES
) -> str:
    statements = (_get_create_statement(connection, table) for table in tables)

    return "\n".join(statements)


def _get_create_statement(connection: DuckDBPyConnection, table: str) -> str:
    rows = connection.execute(
        "SELECT sql FROM duckdb_tables() WHERE table_name = ?", [table]
    ).fetchall()

    if not rows:
        raise ValueError(f"Unknown table: {table}")

    return str(rows[0][0])
