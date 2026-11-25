import unittest

from duckdb import connect

from talk_with_data.schema import _get_create_statement, describe_schema


class TestSchema(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect()
        self.connection.execute("CREATE VIEW alpha AS SELECT 1 AS id, 'x' AS name")
        self.connection.execute(
            "CREATE VIEW beta AS SELECT TIMESTAMP '2018-01-01' AS created"
        )

    def test_describe_schema(self) -> None:
        self.assertEqual(
            describe_schema(self.connection, views=("beta", "alpha")),
            "CREATE VIEW beta(created TIMESTAMP);\n"
            "CREATE VIEW alpha(id INTEGER, name VARCHAR);",
        )
        self.assertEqual(describe_schema(self.connection, views=()), "")

        with self.assertRaises(ValueError):
            describe_schema(self.connection)

    def test_get_create_statement(self) -> None:
        self.assertEqual(
            _get_create_statement(self.connection, "alpha"),
            "CREATE VIEW alpha(id INTEGER, name VARCHAR);",
        )

        with self.assertRaises(ValueError):
            _get_create_statement(self.connection, "delta")


if __name__ == "__main__":
    unittest.main()
