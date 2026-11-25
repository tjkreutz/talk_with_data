import unittest

from duckdb import connect

from talk_with_data.schema import _get_create_statement, describe_schema


class TestSchema(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect()
        self.connection.execute("CREATE TABLE alpha (id INTEGER, name VARCHAR)")
        self.connection.execute("CREATE TABLE beta (created TIMESTAMP)")
        self.connection.execute(
            "CREATE VIEW gamma AS SELECT 1 AS n, DATE '2018-01-01' AS d"
        )

    def test_describe_schema(self) -> None:
        self.assertEqual(
            describe_schema(self.connection, tables=("beta", "alpha", "gamma")),
            "CREATE TABLE beta(created TIMESTAMP);\n"
            "CREATE TABLE alpha(id INTEGER, name VARCHAR);\n"
            "CREATE VIEW gamma(n INTEGER, d DATE);",
        )
        self.assertEqual(describe_schema(self.connection, tables=()), "")

        with self.assertRaises(ValueError):
            describe_schema(self.connection)

    def test_get_create_statement(self) -> None:
        self.assertEqual(
            _get_create_statement(self.connection, "beta"),
            "CREATE TABLE beta(created TIMESTAMP);",
        )
        self.assertEqual(
            _get_create_statement(self.connection, "gamma"),
            "CREATE VIEW gamma(n INTEGER, d DATE);",
        )

        with self.assertRaises(ValueError):
            _get_create_statement(self.connection, "delta")


if __name__ == "__main__":
    unittest.main()
