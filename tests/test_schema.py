import unittest

from duckdb import connect

from talk_with_data.schema import describe_schema, get_create_statement


class TestSchema(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect()
        self.connection.execute("CREATE TABLE alpha (id INTEGER, name VARCHAR)")
        self.connection.execute("CREATE TABLE beta (created TIMESTAMP)")

    def test_describe_schema(self) -> None:
        self.assertEqual(
            describe_schema(self.connection, tables=("beta", "alpha")),
            "CREATE TABLE beta(created TIMESTAMP);\n"
            'CREATE TABLE alpha(id INTEGER, "name" VARCHAR);',
        )
        self.assertEqual(describe_schema(self.connection, tables=()), "")

        with self.assertRaises(ValueError):
            describe_schema(self.connection)

    def test_get_create_statement(self) -> None:
        self.assertEqual(
            get_create_statement(self.connection, "beta"),
            "CREATE TABLE beta(created TIMESTAMP);",
        )

        with self.assertRaises(ValueError):
            get_create_statement(self.connection, "gamma")


if __name__ == "__main__":
    unittest.main()
