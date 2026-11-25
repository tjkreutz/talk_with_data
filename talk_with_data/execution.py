from duckdb import DuckDBPyConnection, StatementType


def run_query(connection: DuckDBPyConnection, sql: str) -> list[tuple[object, ...]]:
    statements = connection.extract_statements(sql)

    if len(statements) != 1 or statements[0].type != StatementType.SELECT:
        raise ValueError("Only a single SELECT statement is allowed")

    return connection.execute(sql).fetchall()
