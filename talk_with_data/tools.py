import logging
from collections.abc import Callable, Iterable, Mapping

from duckdb import DuckDBPyConnection
from openai import OpenAI, pydantic_function_tool
from openai.types.chat import (
    ChatCompletionFunctionToolParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallUnion,
    ParsedFunctionToolCall,
)
from pydantic import BaseModel, Field

from talk_with_data.config import SEARCH_RESULTS
from talk_with_data.search import search_reviews_json

LOGGER = logging.getLogger(__name__)
ToolHandler = Callable[[Mapping[str, object]], str]


class SearchReviews(BaseModel):
    query: str = Field(description="What to look for, for example 'late delivery'.")


TOOLS: dict[str, ChatCompletionFunctionToolParam] = {
    "search_reviews": pydantic_function_tool(
        SearchReviews,
        name="search_reviews",
        description=(
            "Semantic search over the written customer reviews, which are mostly "
            "in Portuguese; a search term in any language works. Returns the "
            f"{SEARCH_RESULTS} reviews closest in meaning, each with review_id, "
            "order_id, review_score, review_text and similarity. Use it to see how "
            "customers talk about a topic, or to find review and order ids."
        ),
    )
}


def make_tools(
    connection: DuckDBPyConnection, client: OpenAI
) -> dict[str, ToolHandler]:
    return {
        "search_reviews": lambda arguments: search_reviews_json(
            connection, client, str(arguments["query"])
        )
    }


def run_tool_calls(
    tool_calls: Iterable[ChatCompletionMessageToolCallUnion],
    tools: Mapping[str, ToolHandler],
) -> list[ChatCompletionMessageParam]:
    return [
        {
            "role": "tool",
            "tool_call_id": call.id,
            "content": _call_tool(call, tools),
        }
        for call in tool_calls
        if isinstance(call, ParsedFunctionToolCall)
    ]


def _call_tool(call: ParsedFunctionToolCall, tools: Mapping[str, ToolHandler]) -> str:
    name = call.function.name
    handler = tools.get(name)
    arguments = call.function.parsed_arguments

    if handler is None or not isinstance(arguments, BaseModel):
        return f"Error: unknown tool {name}"

    try:
        return handler(arguments.model_dump())
    except ValueError as error:
        LOGGER.warning("Bad arguments %s for %s: %s", arguments, name, error)

        return f"Error: invalid arguments for {name}"
