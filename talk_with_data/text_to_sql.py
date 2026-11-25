import os
import re
from collections.abc import Mapping, Sequence
from typing import cast

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionFunctionToolParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
)

from talk_with_data.config import (
    HISTORY_TURNS,
    MAX_TOOL_ROUNDS,
    TEXT_TO_SQL_MODEL,
    TEXT_TO_SQL_PROMPT_NAME,
)
from talk_with_data.tools import TOOLS, ToolHandler, run_tool_calls
from talk_with_data.utils import load_prompt

CODE_BLOCK = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL)


def generate_sql(
    client: OpenAI,
    question: str,
    schema: str,
    tools: Mapping[str, ToolHandler] | None = None,
    history: Sequence[tuple[str, str]] = (),
) -> str:
    messages = _build_messages(question, schema, history)
    definitions = [TOOLS[name] for name in tools or {}]

    for _ in range(MAX_TOOL_ROUNDS):
        message = _complete(client, messages, definitions)

        if not tools or not message.tool_calls:
            return _extract_sql(message.content or "")

        messages.append(
            cast(ChatCompletionMessageParam, message.model_dump(exclude_none=True))
        )
        messages.extend(run_tool_calls(message.tool_calls, tools))

    return _extract_sql(_complete(client, messages, []).content or "")


def _build_messages(
    question: str, schema: str, history: Sequence[tuple[str, str]]
) -> list[ChatCompletionMessageParam]:
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": build_system_prompt(schema)}
    ]

    for past_question, past_sql in history[-HISTORY_TURNS:]:
        messages.append({"role": "user", "content": past_question})
        messages.append({"role": "assistant", "content": f"```sql\n{past_sql}\n```"})

    messages.append({"role": "user", "content": question})

    return messages


def build_system_prompt(schema: str) -> str:
    return load_prompt(TEXT_TO_SQL_PROMPT_NAME).format(schema=schema)


def create_client() -> OpenAI:
    load_dotenv()

    return OpenAI(base_url=os.environ["LLM_API_URL"], api_key=os.environ["LLM_API_KEY"])


def _complete(
    client: OpenAI,
    messages: list[ChatCompletionMessageParam],
    tools: list[ChatCompletionFunctionToolParam],
) -> ChatCompletionMessage:
    if tools:
        parsed = client.chat.completions.parse(
            model=TEXT_TO_SQL_MODEL, messages=messages, tools=tools
        )

        return parsed.choices[0].message

    response = client.chat.completions.create(
        model=TEXT_TO_SQL_MODEL, messages=messages
    )

    return response.choices[0].message


def _extract_sql(reply: str) -> str:
    match = CODE_BLOCK.search(reply)

    return (match.group(1) if match else reply).strip()
