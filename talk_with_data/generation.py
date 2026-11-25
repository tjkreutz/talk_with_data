import json
import logging
import os
import re
from collections.abc import Callable, Iterable
from typing import cast

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionFunctionToolParam,
    ChatCompletionMessage,
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallUnion,
)

from talk_with_data.config import MAX_TOOL_ROUNDS, MODEL, PROMPT_NAME, SEARCH_RESULTS
from talk_with_data.utils import load_prompt

LOGGER = logging.getLogger(__name__)
CODE_BLOCK = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL)
SEARCH_TOOL: ChatCompletionFunctionToolParam = {
    "type": "function",
    "function": {
        "name": "search_reviews",
        "description": (
            "Semantic search over the written customer reviews, which are mostly "
            "in Portuguese; a search term in any language works. Returns the "
            f"{SEARCH_RESULTS} reviews closest in meaning, each with review_id, "
            "order_id, review_score, review_text and similarity. Use it to see how "
            "customers talk about a topic, or to find review and order ids."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to look for, for example 'late delivery'.",
                }
            },
            "required": ["query"],
        },
    },
}


def generate_sql(
    client: OpenAI,
    question: str,
    schema: str,
    search: Callable[[str], str] | None = None,
) -> str:
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": build_system_prompt(schema)},
        {"role": "user", "content": question},
    ]
    tools = [SEARCH_TOOL] if search else []

    for _ in range(MAX_TOOL_ROUNDS):
        message = _complete(client, messages, tools)

        if search is None or not message.tool_calls:
            return _extract_sql(message.content or "")

        messages.append(
            cast(ChatCompletionMessageParam, message.model_dump(exclude_none=True))
        )
        messages.extend(_run_tool_calls(message.tool_calls, search))

    return _extract_sql(_complete(client, messages, []).content or "")


def build_system_prompt(schema: str) -> str:
    return load_prompt(PROMPT_NAME).format(schema=schema)


def create_client() -> OpenAI:
    load_dotenv()

    return OpenAI(base_url=os.environ["LLM_API_URL"], api_key=os.environ["LLM_API_KEY"])


def _complete(
    client: OpenAI,
    messages: list[ChatCompletionMessageParam],
    tools: list[ChatCompletionFunctionToolParam],
) -> ChatCompletionMessage:
    if tools:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=tools
        )
    else:
        response = client.chat.completions.create(model=MODEL, messages=messages)

    return response.choices[0].message


def _run_tool_calls(
    tool_calls: Iterable[ChatCompletionMessageToolCallUnion],
    search: Callable[[str], str],
) -> list[ChatCompletionMessageParam]:
    return [
        {
            "role": "tool",
            "tool_call_id": call.id,
            "content": _call_search(call.function.arguments, search),
        }
        for call in tool_calls
        if isinstance(call, ChatCompletionMessageFunctionToolCall)
    ]


def _call_search(arguments: str, search: Callable[[str], str]) -> str:
    try:
        query = str(json.loads(arguments)["query"])
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        LOGGER.warning("Bad search arguments %r: %s", arguments, error)

        return "Error: call search_reviews with a JSON object with a 'query' string."

    return search(query)


def _extract_sql(reply: str) -> str:
    match = CODE_BLOCK.search(reply)

    return (match.group(1) if match else reply).strip()
