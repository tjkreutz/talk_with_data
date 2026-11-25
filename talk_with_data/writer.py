import json
from collections.abc import Sequence

from openai import OpenAI

from talk_with_data.config import (
    WRITER_MAX_ROWS,
    WRITER_MODEL,
    WRITER_PROMPT_NAME,
    WRITER_TEMPERATURE,
)
from talk_with_data.utils import load_prompt


def write_answer(
    client: OpenAI, question: str, sql: str, rows: Sequence[Sequence[object]]
) -> str:
    response = client.chat.completions.create(
        model=WRITER_MODEL,
        temperature=WRITER_TEMPERATURE,
        messages=[
            {"role": "system", "content": load_prompt(WRITER_PROMPT_NAME)},
            {"role": "user", "content": _format_request(question, sql, rows)},
        ],
    )

    return (response.choices[0].message.content or "").strip()


def _format_request(question: str, sql: str, rows: Sequence[Sequence[object]]) -> str:
    shown = rows[:WRITER_MAX_ROWS]
    note = f", first {len(shown)} shown" if len(shown) < len(rows) else ""
    result = json.dumps(shown, default=str, ensure_ascii=False)

    return f"Question: {question}\n\nSQL:\n{sql}\n\nResult ({len(rows)} rows{note}):\n{result}"
