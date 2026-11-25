import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

from duckdb import connect

from talk_with_data.experiment import (
    _evaluate_attempt,
    _execute_attempt,
    _get_git_version,
    _hash_prompt,
    _preview_rows,
    append_record,
    describe_experiment,
    run_experiment,
    write_attempts,
)
from talk_with_data.generation import MODEL
from talk_with_data.metrics import Attempt
from talk_with_data.questions import Question

RUN = "talk_with_data.experiment.run"
GIT_VERSION = "talk_with_data.experiment._get_git_version"


def _make_question(gold_sql: str) -> Question:
    return Question(id="q1", template="a", question="How many?", gold_sql=gold_sql)


class TestExperiment(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect()

    def test_run_experiment(self) -> None:
        client = MagicMock()
        message = client.chat.completions.create.return_value.choices[0].message
        message.content = "```sql\nSELECT 1\n```"
        questions = [
            Question(id="q1", template="a", question="One?", gold_sql="SELECT 1"),
            Question(id="q2", template="b", question="Two?", gold_sql="SELECT 2"),
        ]

        attempts = run_experiment(
            questions=questions,
            client=client,
            connection=self.connection,
            schema="CREATE TABLE t(a INT);",
            runs=2,
        )

        self.assertEqual(client.chat.completions.create.call_count, 4)
        self.assertEqual(
            [(a.question_id, a.run, a.outcome) for a in attempts],
            [
                ("q1", 1, "correct"),
                ("q2", 1, "wrong"),
                ("q1", 2, "correct"),
                ("q2", 2, "wrong"),
            ],
        )
        self.assertEqual(attempts[1].sql, "SELECT 1")
        self.assertEqual(attempts[1].result, [[1]])
        self.assertEqual(attempts[1].gold, [[2]])

    def test_evaluate_attempt(self) -> None:
        question = _make_question("SELECT 1")

        attempt = _evaluate_attempt(self.connection, "SELECT 2", question, 3, [(1,)])

        self.assertEqual(
            attempt,
            Attempt(
                question_id="q1",
                template="a",
                run=3,
                question="How many?",
                sql="SELECT 2",
                outcome="wrong",
                result=[[2]],
                gold=[[1]],
            ),
        )

    def test_execute_attempt(self) -> None:
        question = _make_question("SELECT 1")
        gold = [(1,)]

        def execute(sql: str) -> tuple[str, object]:
            return _execute_attempt(self.connection, sql, question, gold)

        self.assertEqual(execute("SELECT 1"), ("correct", [[1]]))
        self.assertEqual(execute("SELECT 2"), ("wrong", [[2]]))
        self.assertEqual(execute("SELECT 1 WHERE false"), ("empty", []))

        with self.assertLogs("talk_with_data.experiment", level="WARNING"):
            outcome, result = execute("SELEC nonsense")

        self.assertEqual(outcome, "error")
        self.assertIn("syntax error", str(result).lower())

        with self.assertLogs("talk_with_data.experiment", level="WARNING"):
            self.assertEqual(
                execute("DROP TABLE t"),
                ("error", "Only a single SELECT statement is allowed"),
            )

    def test_describe_experiment(self) -> None:
        with patch(GIT_VERSION, return_value="abc1234+dirty"):
            description = describe_experiment(
                "baseline", "dev", "CREATE TABLE t(a INT);"
            )

        self.assertEqual(
            list(description),
            [
                "id",
                "experiment",
                "timestamp",
                "git_commit",
                "model",
                "prompt_hash",
                "tables",
                "split",
            ],
        )
        self.assertRegex(str(description["id"]), r"^baseline-\d{8}T\d{6}$")
        self.assertEqual(description["experiment"], "baseline")
        self.assertEqual(description["git_commit"], "abc1234+dirty")
        self.assertEqual(description["model"], MODEL)
        self.assertEqual(description["tables"], ["order_facts", "review_facts"])
        self.assertEqual(description["split"], "dev")
        self.assertTrue(str(description["timestamp"]).endswith("+00:00"))

    def test_append_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiments.jsonl"
            append_record({"experiment": "a", "accuracy": 0.5}, path)
            append_record({"experiment": "é"}, path)
            lines = path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(
            [json.loads(line) for line in lines],
            [
                {"experiment": "a", "accuracy": 0.5},
                {"experiment": "é"},
            ],
        )

    def test_write_attempts(self) -> None:
        attempt = Attempt(
            question_id="q1",
            template="a",
            run=1,
            question="Wie viele é?",
            sql="SELECT now()",
            outcome="wrong",
            result=[[datetime(2017, 11, 24, 10, 0)]],
            gold=[[1]],
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs" / "baseline-1.jsonl"
            write_attempts([attempt, attempt], path)
            lines = path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 2)
        self.assertEqual(
            json.loads(lines[0]),
            {
                "question_id": "q1",
                "template": "a",
                "run": 1,
                "question": "Wie viele é?",
                "sql": "SELECT now()",
                "outcome": "wrong",
                "result": [["2017-11-24 10:00:00"]],
                "gold": [[1]],
            },
        )

    def test_preview_rows(self) -> None:
        rows = [(number, "x") for number in range(8)]

        self.assertEqual(_preview_rows(rows), [[number, "x"] for number in range(5)])
        self.assertEqual(_preview_rows(rows[:2]), [[0, "x"], [1, "x"]])
        self.assertEqual(_preview_rows([]), [])

    def test_hash_prompt(self) -> None:
        first = _hash_prompt("CREATE TABLE t(a INT);")

        self.assertEqual(len(first), 8)
        self.assertEqual(first, _hash_prompt("CREATE TABLE t(a INT);"))
        self.assertNotEqual(first, _hash_prompt("CREATE TABLE t(b INT);"))

    def test_get_git_version(self) -> None:
        def completed(stdout: str) -> CompletedProcess[str]:
            return CompletedProcess(args=[], returncode=0, stdout=stdout)

        with patch(RUN, side_effect=[completed("abc1234\n"), completed("")]):
            self.assertEqual(_get_git_version(), "abc1234")

        with patch(
            RUN, side_effect=[completed("abc1234\n"), completed(" M file.py\n")]
        ):
            self.assertEqual(_get_git_version(), "abc1234+dirty")


if __name__ == "__main__":
    unittest.main()
