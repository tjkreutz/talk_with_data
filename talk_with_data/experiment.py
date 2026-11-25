import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from duckdb import DuckDBPyConnection
from openai import OpenAI

from talk_with_data.comparison import results_match
from talk_with_data.config import (
    HASH_LENGTH,
    MAX_WORKERS,
    PREVIEW_ROWS,
    TEXT_TO_SQL_MODEL,
    VIEWS,
)
from talk_with_data.execution import run_query, try_query
from talk_with_data.metrics import Attempt, Outcome
from talk_with_data.questions import Question
from talk_with_data.text_to_sql import build_system_prompt, generate_sql
from talk_with_data.utils import get_git_version, write_jsonl

LOGGER = logging.getLogger(__name__)


def run_experiment(
    questions: Sequence[Question],
    client: OpenAI,
    connection: DuckDBPyConnection,
    schema: str,
    runs: int,
) -> list[Attempt]:
    jobs = [(question, run) for run in range(1, runs + 1) for question in questions]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        sqls = list(
            executor.map(
                lambda job: generate_sql(client, job[0].question, schema), jobs
            )
        )

    gold_rows = {q.id: run_query(connection, q.gold_sql) for q in questions}

    return [
        _evaluate_attempt(connection, sql, question, run, gold_rows[question.id])
        for (question, run), sql in zip(jobs, sqls, strict=True)
    ]


def _evaluate_attempt(
    connection: DuckDBPyConnection,
    sql: str,
    question: Question,
    run: int,
    gold_rows: Sequence[Sequence[object]],
) -> Attempt:
    outcome, result = _execute_attempt(connection, sql, question, gold_rows)

    return Attempt(
        question_id=question.id,
        template=question.template,
        run=run,
        question=question.question,
        sql=sql,
        outcome=outcome,
        result=result,
        gold=_preview_rows(gold_rows),
    )


def _execute_attempt(
    connection: DuckDBPyConnection,
    sql: str,
    question: Question,
    gold_rows: Sequence[Sequence[object]],
) -> tuple[Outcome, object]:
    result = try_query(connection, sql)

    if result.error is not None:
        LOGGER.warning("%s: %s", question.id, result.error)

        return "error", result.error

    predicted = result.rows
    preview = _preview_rows(predicted)

    if results_match(predicted, gold_rows):
        return "correct", preview

    return ("wrong" if predicted else "empty"), preview


def describe_experiment(name: str, split: str, schema: str) -> dict[str, object]:
    now = datetime.now(UTC)

    return {
        "id": f"{name}-{now:%Y%m%dT%H%M%S}",
        "experiment": name,
        "timestamp": now.isoformat(timespec="seconds"),
        "git_commit": get_git_version(),
        "model": TEXT_TO_SQL_MODEL,
        "prompt_hash": _hash_prompt(schema),
        "tables": list(VIEWS),
        "split": split,
    }


def write_attempts(attempts: Sequence[Attempt], path: Path) -> None:
    write_jsonl((asdict(attempt) for attempt in attempts), path)


def _preview_rows(rows: Sequence[Sequence[object]]) -> list[list[object]]:
    return [list(row) for row in rows[:PREVIEW_ROWS]]


def _hash_prompt(schema: str) -> str:
    prompt = build_system_prompt(schema)

    return sha256(prompt.encode()).hexdigest()[:HASH_LENGTH]
