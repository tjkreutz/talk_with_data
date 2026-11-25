import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from talk_with_data.utils import (
    append_jsonl,
    get_git_version,
    group_by,
    load_prompt,
    load_sql,
    write_jsonl,
)

RUN = "talk_with_data.utils.run"


class TestUtils(unittest.TestCase):
    def test_load_sql(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sql_dir = Path(directory)
            (sql_dir / "orders.sql").write_text("SELECT é\nFROM t\n", encoding="utf-8")

            self.assertEqual(load_sql("orders", sql_dir), "SELECT é\nFROM t\n")

            with self.assertRaises(FileNotFoundError):
                load_sql("missing", sql_dir)

    def test_load_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prompt_dir = Path(directory)
            (prompt_dir / "system.txt").write_text("Write é {schema}", encoding="utf-8")

            self.assertEqual(load_prompt("system", prompt_dir), "Write é {schema}")

            with self.assertRaises(FileNotFoundError):
                load_prompt("missing", prompt_dir)

    def test_append_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiments.jsonl"
            append_jsonl({"experiment": "a", "accuracy": 0.5}, path)
            append_jsonl({"experiment": "é"}, path)
            lines = path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(
            [json.loads(line) for line in lines],
            [{"experiment": "a", "accuracy": 0.5}, {"experiment": "é"}],
        )

    def test_write_jsonl(self) -> None:
        rows = [
            {"id": 1, "when": datetime(2017, 11, 24, 10, 0)},
            {"id": 2, "text": "é"},
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "rows.jsonl"
            write_jsonl(iter(rows), path)
            write_jsonl(iter(rows[1:]), path)
            lines = path.read_text(encoding="utf-8").splitlines()

        self.assertEqual([json.loads(line) for line in lines], [{"id": 2, "text": "é"}])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"
            write_jsonl(rows, path)
            lines = path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(json.loads(lines[0]), {"id": 1, "when": "2017-11-24 10:00:00"})

    def test_group_by(self) -> None:
        words = ["apple", "avocado", "banana", "blueberry", "cherry"]

        groups = group_by(words, lambda word: word[0])

        self.assertEqual(list(groups), ["a", "b", "c"])
        self.assertEqual(groups["a"], ["apple", "avocado"])
        self.assertEqual(groups["c"], ["cherry"])
        self.assertEqual(group_by([], len), {})
        self.assertEqual(group_by(iter(words[:2]), len), {5: ["apple"], 7: ["avocado"]})

    def test_get_git_version(self) -> None:
        def completed(stdout: str) -> CompletedProcess[str]:
            return CompletedProcess(args=[], returncode=0, stdout=stdout)

        with patch(RUN, side_effect=[completed("abc1234\n"), completed("")]):
            self.assertEqual(get_git_version(), "abc1234")

        with patch(
            RUN, side_effect=[completed("abc1234\n"), completed(" M file.py\n")]
        ):
            self.assertEqual(get_git_version(), "abc1234+dirty")


if __name__ == "__main__":
    unittest.main()
