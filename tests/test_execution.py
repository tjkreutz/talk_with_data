import unittest
from unittest.mock import patch

from duckdb import OutOfMemoryException, ProgrammingError, connect

from talk_with_data.execution import (
    NotSelectError,
    QueryResult,
    run_query,
    try_query,
)


class TestExecution(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect()
        self.connection.execute("CREATE TABLE t (a INTEGER)")
        self.connection.execute("INSERT INTO t VALUES (1), (2)")

    def test_try_query(self) -> None:
        self.assertEqual(
            try_query(self.connection, "SELECT a FROM t ORDER BY a"),
            QueryResult(rows=[(1,), (2,)]),
        )

        failures = {
            "unknown table": "SELECT * FROM missing",
            "unknown column": "SELECT nope FROM t",
            "syntax": "SELEC 1",
            "text instead of sql": "I cannot answer that",
            "file read": "SELECT * FROM read_parquet('nope.parquet')",
            "bad cast": "SELECT CAST('x' AS INTEGER)",
            "overflow": "SELECT 9223372036854775807 + 1",
            "not a select": "DROP TABLE t",
            "two statements": "SELECT 1; SELECT 2",
        }

        for label, sql in failures.items():
            result = try_query(self.connection, sql)

            self.assertEqual(result.rows, [], label)
            self.assertTrue(result.error, label)

        self.assertEqual(run_query(self.connection, "SELECT count(*) FROM t"), [(2,)])

        for error in (OutOfMemoryException("full"), RuntimeError("bug")):
            with (
                patch("talk_with_data.execution.run_query", side_effect=error),
                self.assertRaises(type(error)),
            ):
                try_query(self.connection, "SELECT 1")

    def test_run_query(self) -> None:
        self.assertEqual(
            run_query(self.connection, "SELECT a FROM t ORDER BY a;"), [(1,), (2,)]
        )
        self.assertEqual(
            run_query(self.connection, "WITH x AS (SELECT 5 AS v) SELECT v FROM x"),
            [(5,)],
        )

        for sql in (
            "DROP TABLE t",
            "INSERT INTO t VALUES (3)",
            "SELECT 1; DROP TABLE t",
            "SELECT 1; SELECT 2",
            "",
        ):
            with self.assertRaises(NotSelectError):
                run_query(self.connection, sql)

        with self.assertRaises(ProgrammingError):
            run_query(self.connection, "SELEC nonsense")

        self.assertEqual(run_query(self.connection, "SELECT count(*) FROM t"), [(2,)])


if __name__ == "__main__":
    unittest.main()
