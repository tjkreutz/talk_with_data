import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from duckdb import DuckDBPyConnection, connect

from talk_with_data.answer import FAILURE, Answer, answer_question, stream_answer

PIECES = ["There ", "is ", "one row."]


class TestAnswer(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect()
        self.connection.execute("CREATE TABLE t AS SELECT 1 AS n")
        self.client = MagicMock()

    @contextmanager
    def _model(self, sql: str) -> Iterator[MagicMock]:
        write = MagicMock(side_effect=lambda *arguments: iter(PIECES))

        with (
            patch("talk_with_data.answer.generate_sql", return_value=sql) as generate,
            patch("talk_with_data.answer.write_answer", write),
        ):
            yield write

        generate.assert_called_once_with(self.client, "How many?", "SCHEMA")

    def _ask(self) -> tuple[DuckDBPyConnection, MagicMock, str, str]:
        return self.connection, self.client, "SCHEMA", "How many?"

    def test_answer_question(self) -> None:
        with self._model("SELECT n FROM t") as write:
            answer = answer_question(*self._ask())

        self.assertEqual(
            answer, Answer(sql="SELECT n FROM t", rows=[(1,)], text="There is one row.")
        )
        write.assert_called_once_with(
            self.client, "How many?", "SELECT n FROM t", [(1,)]
        )

        with self._model("SELECT * FROM missing") as write:
            answer = answer_question(*self._ask())

        self.assertEqual(answer.text, FAILURE)
        self.assertEqual(answer.rows, [])
        self.assertTrue(answer.error)
        write.assert_not_called()

    def test_stream_answer(self) -> None:
        with self._model("SELECT n FROM t"):
            stages = list(stream_answer(*self._ask()))

        self.assertEqual(
            stages,
            [
                Answer(sql="SELECT n FROM t"),
                Answer(sql="SELECT n FROM t", rows=[(1,)]),
                Answer(sql="SELECT n FROM t", rows=[(1,)], text="There"),
                Answer(sql="SELECT n FROM t", rows=[(1,)], text="There is"),
                Answer(sql="SELECT n FROM t", rows=[(1,)], text="There is one row."),
            ],
        )

        for sql in (
            "SELECT * FROM missing",
            "SELECT nope FROM t",
            "I cannot answer that",
        ):
            with self._model(sql) as write:
                stages = list(stream_answer(*self._ask()))

            self.assertEqual(len(stages), 2, sql)
            self.assertEqual(stages[0], Answer(sql=sql), sql)
            self.assertEqual((stages[1].rows, stages[1].text), ([], FAILURE), sql)
            self.assertTrue(stages[1].error, sql)
            write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
