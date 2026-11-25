import unittest

from duckdb import Error, connect

from talk_with_data.execution import run_query


class TestExecution(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect()
        self.connection.execute("CREATE TABLE t (a INTEGER)")
        self.connection.execute("INSERT INTO t VALUES (1), (2)")

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
            with self.assertRaises(ValueError):
                run_query(self.connection, sql)

        with self.assertRaises(Error):
            run_query(self.connection, "SELEC nonsense")

        self.assertEqual(run_query(self.connection, "SELECT count(*) FROM t"), [(2,)])


if __name__ == "__main__":
    unittest.main()
