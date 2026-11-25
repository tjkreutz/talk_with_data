import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageParam

from talk_with_data.config import MAX_TOOL_ROUNDS, MODEL
from talk_with_data.generation import (
    SEARCH_TOOL,
    _call_search,
    _complete,
    _extract_sql,
    _run_tool_calls,
    build_system_prompt,
    generate_sql,
)

LOAD_DOTENV = "talk_with_data.generation.load_dotenv"


def _tool_message(*queries: str) -> ChatCompletionMessage:
    return ChatCompletionMessage.model_validate(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"call_{index}",
                    "type": "function",
                    "function": {
                        "name": "search_reviews",
                        "arguments": query
                        if query.startswith("{")
                        else '{"query": "' + query + '"}',
                    },
                }
                for index, query in enumerate(queries, start=1)
            ],
        }
    )


def _response(message: ChatCompletionMessage | SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _answer(sql: str) -> SimpleNamespace:
    return SimpleNamespace(content=f"```sql\n{sql}\n```", tool_calls=None)


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
        self.assertNotIn("tools", call)

        message.content = None

        self.assertEqual(generate_sql(client, question="?", schema=""), "")

    def test_generate_sql_with_search(self) -> None:
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            _response(_tool_message("late delivery")),
            _response(_answer("SELECT 2")),
        ]
        search = MagicMock(return_value='[{"review_id": "r1"}]')

        sql = generate_sql(client, question="Q?", schema="S", search=search)

        self.assertEqual(sql, "SELECT 2")
        search.assert_called_once_with("late delivery")
        first, second = (
            call.kwargs for call in client.chat.completions.create.call_args_list
        )
        self.assertEqual(first["tools"], [SEARCH_TOOL])
        self.assertEqual(second["messages"][-2]["role"], "assistant")
        self.assertEqual(second["messages"][-2]["tool_calls"][0]["id"], "call_1")
        self.assertEqual(
            second["messages"][-1],
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "content": '[{"review_id": "r1"}]',
            },
        )

    def test_generate_sql_stops_after_the_tool_rounds(self) -> None:
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            *[_response(_tool_message("x")) for _ in range(MAX_TOOL_ROUNDS)],
            _response(_answer("SELECT 3")),
        ]

        sql = generate_sql(client, "Q?", "S", search=MagicMock(return_value="[]"))

        self.assertEqual(sql, "SELECT 3")
        self.assertEqual(client.chat.completions.create.call_count, MAX_TOOL_ROUNDS + 1)
        self.assertNotIn("tools", client.chat.completions.create.call_args.kwargs)

    def test_complete(self) -> None:
        client = MagicMock()
        client.chat.completions.create.return_value = _response(_answer("SELECT 1"))
        messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": "Q?"}]

        message = _complete(client, messages, [SEARCH_TOOL])

        self.assertEqual(message.content, "```sql\nSELECT 1\n```")
        self.assertEqual(
            client.chat.completions.create.call_args.kwargs["tools"], [SEARCH_TOOL]
        )

        _complete(client, messages, [])

        self.assertNotIn("tools", client.chat.completions.create.call_args.kwargs)
        self.assertEqual(
            client.chat.completions.create.call_args.kwargs["model"], MODEL
        )

    def test_run_tool_calls(self) -> None:
        search = MagicMock(side_effect=lambda query: f"results for {query}")
        message = _tool_message("late delivery", "broken")

        results = _run_tool_calls(message.tool_calls or [], search)

        self.assertEqual(
            results,
            [
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "content": "results for late delivery",
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_2",
                    "content": "results for broken",
                },
            ],
        )
        self.assertEqual(_run_tool_calls([], search), [])

    def test_call_search(self) -> None:
        search = MagicMock(return_value="[]")

        self.assertEqual(_call_search('{"query": "entrega"}', search), "[]")
        search.assert_called_once_with("entrega")

        for arguments in ("not json", '{"other": 1}', "[1, 2]"):
            with self.assertLogs("talk_with_data.generation", level="WARNING"):
                reply = _call_search(arguments, search)

            self.assertTrue(reply.startswith("Error:"))

        search.assert_called_once()

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
