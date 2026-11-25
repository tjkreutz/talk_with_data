from dataclasses import dataclass

from duckdb import DuckDBPyConnection
from streamlit import (
    cache_resource,
    chat_input,
    chat_message,
    empty,
    markdown,
    session_state,
)
from streamlit.delta_generator import DeltaGenerator

from talk_with_data.answer import Answer, stream_answer
from talk_with_data.database import create_connection
from talk_with_data.schema import describe_schema
from talk_with_data.text_to_sql import create_client

PLACEHOLDER = "Ask a question about Olist orders and reviews"
TURNS = "turns"


@dataclass(frozen=True)
class Turn:
    question: str
    answer: Answer


def main() -> None:
    if TURNS not in session_state:
        session_state[TURNS] = []

    turns: list[Turn] = session_state[TURNS]

    for turn in turns:
        _show_turn(turn)

    question = chat_input(PLACEHOLDER)

    if not question:
        return

    with chat_message("user"):
        markdown(question)

    connection = _get_connection()
    schema = describe_schema(connection)
    history = [(t.question, t.answer.sql) for t in turns if t.answer.error is None]

    with chat_message("assistant"):
        slots = (empty(), empty(), empty())

        for answer in stream_answer(
            connection, create_client(), schema, question, history
        ):
            _show(answer, *slots)

    turns.append(Turn(question, answer))


def _show_turn(turn: Turn) -> None:
    with chat_message("user"):
        markdown(turn.question)

    with chat_message("assistant"):
        _show(turn.answer, empty(), empty(), empty())


def _show(
    answer: Answer, sql: DeltaGenerator, result: DeltaGenerator, text: DeltaGenerator
) -> None:
    sql.code(answer.sql, language="sql")

    if answer.error is not None:
        result.caption(answer.error)
        text.warning(answer.text)
    elif answer.rows is not None:
        result.dataframe(answer.rows)

    if answer.error is None and answer.text:
        text.markdown(answer.text)


@cache_resource
def _get_connection() -> DuckDBPyConnection:
    return create_connection()


if __name__ == "__main__":
    main()
