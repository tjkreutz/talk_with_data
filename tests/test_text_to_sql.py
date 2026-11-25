import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openai.types.chat import (
    ChatCompletionMessageParam,
    ParsedChatCompletionMessage,
    ParsedFunctionToolCall,
)
from openai.types.chat.parsed_function_tool_call import ParsedFunction

from talk_with_data.config import MAX_TOOL_ROUNDS, MODEL
from talk_with_data.text_to_sql import (
    _complete,
    _extract_sql,
    build_system_prompt,
    generate_sql,
)
from talk_with_data.tools import TOOLS, SearchReviews

LOAD_DOTENV = "talk_with_data.text_to_sql.load_dotenv"


def _tool_message(*queries: str) -> ParsedChatCompletionMessage[None]:
    return ParsedChatCompletionMessage[None](
        role="assistant",
        content=None,
        tool_calls=[
            ParsedFunctionToolCall(
                id=f"call_{index}",
                type="function",
                function=ParsedFunction(
                    name="search_reviews",
                    arguments='{"query": "' + query + '"}',
                    parsed_arguments=SearchReviews(query=query),
                ),
            )
            for index, query in enumerate(queries, start=1)
        ],
    )


def _response(
    message: ParsedChatCompletionMessage[None] | SimpleNamespace,
) -> SimpleNamespace:
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
        client.chat.completions.parse.side_effect = [
            _response(_tool_message("late delivery")),
            _response(_answer("SELECT 2")),
        ]
        run = MagicMock(return_value='[{"review_id": "r1"}]')

        sql = generate_sql(
            client, question="Q?", schema="S", tools={"search_reviews": run}
        )

        self.assertEqual(sql, "SELECT 2")
        run.assert_called_once_with({"query": "late delivery"})
        first, second = (
            call.kwargs for call in client.chat.completions.parse.call_args_list
        )
        self.assertEqual(first["tools"], [TOOLS["search_reviews"]])
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
        client.chat.completions.parse.side_effect = [
            _response(_tool_message("x")) for _ in range(MAX_TOOL_ROUNDS)
        ]
        client.chat.completions.create.return_value = _response(_answer("SELECT 3"))
        tools = {"search_reviews": MagicMock(return_value="[]")}

        sql = generate_sql(client, "Q?", "S", tools=tools)

        self.assertEqual(sql, "SELECT 3")
        self.assertEqual(client.chat.completions.parse.call_count, MAX_TOOL_ROUNDS)
        self.assertNotIn("tools", client.chat.completions.create.call_args.kwargs)

    def test_generate_sql_with_history(self) -> None:
        client = MagicMock()
        message = client.chat.completions.create.return_value.choices[0].message
        message.content = "```sql\nSELECT 2\n```"
        history = [("Q1?", "SELECT 1"), ("Q2?", "SELECT 3")]

        sql = generate_sql(client, "And now?", "S", history=history)

        self.assertEqual(sql, "SELECT 2")
        messages = client.chat.completions.create.call_args.kwargs["messages"]
        self.assertEqual(
            [(m["role"], m["content"]) for m in messages[1:]],
            [
                ("user", "Q1?"),
                ("assistant", "```sql\nSELECT 1\n```"),
                ("user", "Q2?"),
                ("assistant", "```sql\nSELECT 3\n```"),
                ("user", "And now?"),
            ],
        )

        with patch("talk_with_data.text_to_sql.HISTORY_TURNS", 1):
            generate_sql(client, "And now?", "S", history=history)

        bounded = client.chat.completions.create.call_args.kwargs["messages"]

        self.assertEqual(len(bounded), 4)
        self.assertEqual(bounded[1]["content"], "Q2?")

    def test_complete(self) -> None:
        client = MagicMock()
        client.chat.completions.parse.return_value = _response(_answer("SELECT 1"))
        client.chat.completions.create.return_value = _response(_answer("SELECT 2"))
        messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": "Q?"}]
        definitions = [TOOLS["search_reviews"]]

        with_tools = _complete(client, messages, definitions)

        self.assertEqual(with_tools.content, "```sql\nSELECT 1\n```")
        parse_call = client.chat.completions.parse.call_args.kwargs
        self.assertEqual(parse_call["tools"], definitions)
        self.assertEqual(parse_call["model"], MODEL)
        client.chat.completions.create.assert_not_called()

        without_tools = _complete(client, messages, [])

        self.assertEqual(without_tools.content, "```sql\nSELECT 2\n```")
        create_call = client.chat.completions.create.call_args.kwargs
        self.assertNotIn("tools", create_call)
        self.assertEqual(create_call["model"], MODEL)

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
