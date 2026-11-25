import unittest
from unittest.mock import MagicMock, patch

from openai.types.chat import ParsedFunctionToolCall
from openai.types.chat.parsed_function_tool_call import ParsedFunction

from talk_with_data.tools import (
    TOOLS,
    SearchReviews,
    ToolHandler,
    _call_tool,
    make_tools,
    run_tool_calls,
)

SEARCH_JSON = "talk_with_data.tools.search_reviews_json"


def _call(index: int, name: str, query: str | None) -> ParsedFunctionToolCall:
    parsed = SearchReviews(query=query) if query is not None else None

    return ParsedFunctionToolCall(
        id=f"call_{index}",
        type="function",
        function=ParsedFunction(
            name=name, arguments=f'{{"query": "{query}"}}', parsed_arguments=parsed
        ),
    )


def _echo(name: str) -> ToolHandler:
    return lambda arguments: f"{name}: {arguments['query']}"


class TestTools(unittest.TestCase):
    def test_tools(self) -> None:
        function = TOOLS["search_reviews"]["function"]

        self.assertEqual(function["name"], "search_reviews")
        self.assertIn("Semantic search", function.get("description", ""))
        self.assertEqual(function.get("parameters", {}).get("required"), ["query"])

    def test_make_tools(self) -> None:
        connection, client = MagicMock(), MagicMock()

        with patch(SEARCH_JSON, return_value="[]") as search:
            tools = make_tools(connection, client)

            self.assertEqual(list(tools), list(TOOLS))
            self.assertEqual(tools["search_reviews"]({"query": "entrega"}), "[]")
            search.assert_called_once_with(connection, client, "entrega")

    def test_run_tool_calls(self) -> None:
        calls = [_call(1, "first", "a"), _call(2, "second", "b")]

        results = run_tool_calls(
            calls, {"first": _echo("first"), "second": _echo("second")}
        )

        self.assertEqual(
            results,
            [
                {"role": "tool", "tool_call_id": "call_1", "content": "first: a"},
                {"role": "tool", "tool_call_id": "call_2", "content": "second: b"},
            ],
        )
        self.assertEqual(run_tool_calls([], {"first": _echo("first")}), [])
        self.assertEqual(
            run_tool_calls([_call(1, "third", "a")], {"first": _echo("first")})[0][
                "content"
            ],
            "Error: unknown tool third",
        )

    def test_call_tool(self) -> None:
        tools = {"echo": _echo("echo")}

        self.assertEqual(_call_tool(_call(1, "echo", "x"), tools), "echo: x")
        self.assertEqual(
            _call_tool(_call(1, "other", "x"), tools), "Error: unknown tool other"
        )
        self.assertEqual(
            _call_tool(_call(1, "echo", None), tools), "Error: unknown tool echo"
        )

        failing = {"echo": MagicMock(side_effect=ValueError("empty"))}

        with self.assertLogs("talk_with_data.tools", level="WARNING"):
            reply = _call_tool(_call(1, "echo", "x"), failing)

        self.assertEqual(reply, "Error: invalid arguments for echo")


if __name__ == "__main__":
    unittest.main()
