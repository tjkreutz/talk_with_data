from dataclasses import dataclass

from duckdb import (
    DataError,
    DuckDBPyConnection,
    IOException,
    ProgrammingError,
    StatementType,
)


class NotSelectError(ValueError):
    pass


QUERY_ERRORS = (ProgrammingError, DataError, IOException, NotSelectError)


@dataclass(frozen=True)
class QueryResult:
    rows: list[tuple[object, ...]]
    error: str | None = None


def try_query(connection: DuckDBPyConnection, sql: str) -> QueryResult:
    try:
        return QueryResult(rows=run_query(connection, sql))
    except QUERY_ERRORS as error:
        return QueryResult(rows=[], error=str(error))


def run_query(connection: DuckDBPyConnection, sql: str) -> list[tuple[object, ...]]:
    statements = connection.extract_statements(sql)

    if len(statements) != 1 or statements[0].type != StatementType.SELECT:
        raise NotSelectError("Only a single SELECT statement is allowed")

    return connection.execute(sql).fetchall()
