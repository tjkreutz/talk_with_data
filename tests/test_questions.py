import tempfile
import unittest
from pathlib import Path

from talk_with_data.questions import Question, load_questions

LINES = (
    '{"id": "a-1", "template": "a", "question": "Wie viele é?", "gold_sql": "SELECT 1"}\n'
    "\n"
    '{"id": "b-1", "template": "b", "question": "How many?", "gold_sql": "SELECT 2"}\n'
)


class TestQuestions(unittest.TestCase):
    def test_load_questions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dev.jsonl"
            path.write_text(LINES, encoding="utf-8")

            questions = load_questions(path)

        self.assertEqual(
            questions,
            [
                Question(
                    id="a-1", template="a", question="Wie viele é?", gold_sql="SELECT 1"
                ),
                Question(
                    id="b-1", template="b", question="How many?", gold_sql="SELECT 2"
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
