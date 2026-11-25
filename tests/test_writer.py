import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from talk_with_data.config import WRITER_MODEL, WRITER_PROMPT_NAME, WRITER_TEMPERATURE
from talk_with_data.utils import load_prompt
from talk_with_data.writer import _format_request, write_answer


def _chunk(content: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content))]
    )


class TestWriter(unittest.TestCase):
    def test_write_answer(self) -> None:
        client = MagicMock()
        client.chat.completions.create.return_value = iter(
            [
                _chunk("There"),
                _chunk(None),
                SimpleNamespace(choices=[]),
                _chunk(" were"),
                _chunk(""),
                _chunk(" 3 orders."),
            ]
        )

        pieces = list(write_answer(client, "How many?", "SELECT 3 AS orders", [(3,)]))

        self.assertEqual(pieces, ["There", " were", " 3 orders."])
        call = client.chat.completions.create.call_args.kwargs
        self.assertEqual(call["model"], WRITER_MODEL)
        self.assertEqual(call["temperature"], WRITER_TEMPERATURE)
        self.assertTrue(call["stream"])
        self.assertEqual(
            call["messages"][0],
            {"role": "system", "content": load_prompt(WRITER_PROMPT_NAME)},
        )
        self.assertEqual(call["messages"][1]["role"], "user")
        self.assertEqual(
            call["messages"][1]["content"],
            _format_request("How many?", "SELECT 3 AS orders", [(3,)]),
        )

        client.chat.completions.create.return_value = iter([])

        self.assertEqual(list(write_answer(client, "?", "SELECT 1", [])), [])

    def test_format_request(self) -> None:
        request = _format_request(
            "Quantos?", "SELECT 1", [("são paulo", date(2017, 11, 24), None)]
        )

        self.assertEqual(
            request,
            "Question: Quantos?\n\nSQL:\nSELECT 1\n\nResult (1 rows):\n"
            '[["são paulo", "2017-11-24", null]]',
        )
        self.assertTrue(
            _format_request("?", "SELECT 1", []).endswith("Result (0 rows):\n[]")
        )

        with patch("talk_with_data.writer.WRITER_MAX_ROWS", 2):
            truncated = _format_request("?", "SELECT 1", [(1,), (2,), (3,)])

        self.assertIn("Result (3 rows, first 2 shown):\n[[1], [2]]", truncated)


if __name__ == "__main__":
    unittest.main()
