import unittest
from unittest.mock import MagicMock

from talk_with_data.config import MODEL
from talk_with_data.generation import (
    _extract_sql,
    build_system_prompt,
    generate_sql,
)

LOAD_DOTENV = "talk_with_data.generation.load_dotenv"


class TestGeneration(unittest.TestCase):
    def test_generate_sql(self) -> None:
        client = MagicMock()
        message = client.chat.completions.create.return_value.choices[0].message
        message.content = "```sql\nSELECT 1\n```"

        sql = generate_sql(
            client, question="How many?", schema="CREATE TABLE t(a INT);"
        )

        self.assertEqual(sql, "SELECT 1")
        call = client.chat.completions.create.call_args.kwargs
        self.assertEqual(call["model"], MODEL)
        self.assertEqual(call["messages"][0]["role"], "system")
        self.assertIn("CREATE TABLE t(a INT);", call["messages"][0]["content"])
        self.assertEqual(call["messages"][1], {"role": "user", "content": "How many?"})

        message.content = None

        self.assertEqual(generate_sql(client, question="?", schema=""), "")

    def test_build_system_prompt(self) -> None:
        prompt = build_system_prompt("CREATE TABLE t(a INT);")

        self.assertIn("CREATE TABLE t(a INT);", prompt)
        self.assertNotIn("{schema}", prompt)
        self.assertIn("Glossary:", prompt)
        self.assertIn("Examples:", prompt)
        self.assertTrue(prompt.endswith("Do not explain."))

    def test_extract_sql(self) -> None:
        self.assertEqual(_extract_sql("```sql\nSELECT 1\n```"), "SELECT 1")
        self.assertEqual(_extract_sql("```\nSELECT 2\n```"), "SELECT 2")
        self.assertEqual(
            _extract_sql("Sure!\n```sql\nSELECT 3;\n```\nDone."), "SELECT 3;"
        )
        self.assertEqual(_extract_sql("  SELECT 4  "), "SELECT 4")
        self.assertEqual(_extract_sql(""), "")


if __name__ == "__main__":
    unittest.main()
