import unittest
from unittest.mock import MagicMock, patch

from duckdb import connect

from talk_with_data.answer import FAILURE, answer_question


class TestAnswer(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect()
        self.connection.execute("CREATE TABLE t AS SELECT 1 AS n")
        self.client = MagicMock()

    def _answer(self, sql: str) -> tuple[str, MagicMock]:
        write = MagicMock(return_value="There is one row.")

        with (
            patch("talk_with_data.answer.generate_sql", return_value=sql) as generate,
            patch("talk_with_data.answer.write_answer", write),
        ):
            reply = answer_question(self.connection, self.client, "SCHEMA", "How many?")

        generate.assert_called_once_with(self.client, "How many?", "SCHEMA")

        return reply, write

    def test_answer_question(self) -> None:
        reply, write = self._answer("SELECT n FROM t")

        self.assertEqual(reply, "There is one row.")
        write.assert_called_once_with(
            self.client, "How many?", "SELECT n FROM t", [(1,)]
        )

        for sql in (
            "SELECT * FROM missing",
            "SELECT nope FROM t",
            "I cannot answer that",
        ):
            reply, write = self._answer(sql)

            self.assertEqual(reply, FAILURE, sql)
            write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
