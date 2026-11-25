from collections.abc import Sequence

from duckdb import DuckDBPyConnection

MODEL_TABLES = ("order_facts", "review_facts")


def describe_schema(
    connection: DuckDBPyConnection, tables: Sequence[str] = MODEL_TABLES
) -> str:
    statements = (_get_create_statement(connection, table) for table in tables)

    return "\n".join(statements)


def _get_create_statement(connection: DuckDBPyConnection, table: str) -> str:
    rows = connection.execute(
        """
        SELECT t.table_type, c.column_name, c.data_type
        FROM information_schema.tables t
        JOIN information_schema.columns c USING (table_schema, table_name)
        WHERE t.table_name = ?
        ORDER BY c.ordinal_position
        """,
        [table],
    ).fetchall()

    if not rows:
        raise ValueError(f"Unknown table: {table}")

    kind = "VIEW" if rows[0][0] == "VIEW" else "TABLE"
    columns = ", ".join(f"{name} {data_type}" for _, name, data_type in rows)

    return f"CREATE {kind} {table}({columns});"
