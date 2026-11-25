import json
import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from subprocess import run

from duckdb import DuckDBPyConnection, Error
from openai import OpenAI

from talk_with_data.comparison import results_match
from talk_with_data.execution import run_query
from talk_with_data.generation import MODEL, SYSTEM_PROMPT, generate_sql
from talk_with_data.metrics import Attempt, Outcome
from talk_with_data.questions import Question
from talk_with_data.schema import CORE_TABLES

LOGGER = logging.getLogger(__name__)
MAX_WORKERS = 8
HASH_LENGTH = 8
PREVIEW_ROWS = 5


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
    try:
        predicted = run_query(connection, sql)
    except (Error, ValueError) as error:
        LOGGER.warning("%s: %s", question.id, error)

        return "error", str(error)

    preview = _preview_rows(predicted)

    if results_match(predicted, gold_rows, question.gold_sql):
        return "correct", preview

    return ("wrong" if predicted else "empty"), preview


def describe_experiment(name: str, split: str, schema: str) -> dict[str, object]:
    now = datetime.now(UTC)

    return {
        "id": f"{name}-{now:%Y%m%dT%H%M%S}",
        "experiment": name,
        "timestamp": now.isoformat(timespec="seconds"),
        "git_commit": _get_git_version(),
        "model": MODEL,
        "prompt_hash": _hash_prompt(schema),
        "tables": list(CORE_TABLES),
        "split": split,
    }


def append_record(record: dict[str, object], path: Path) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(f"{json.dumps(record, ensure_ascii=False)}\n")


def write_attempts(attempts: Sequence[Attempt], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = (
        json.dumps(asdict(attempt), ensure_ascii=False, default=str)
        for attempt in attempts
    )
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def _preview_rows(rows: Sequence[Sequence[object]]) -> list[list[object]]:
    return [list(row) for row in rows[:PREVIEW_ROWS]]


def _hash_prompt(schema: str) -> str:
    prompt = SYSTEM_PROMPT.format(schema=schema)

    return sha256(prompt.encode()).hexdigest()[:HASH_LENGTH]


def _get_git_version() -> str:
    commit = run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    changes = run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
    ).stdout.strip()

    return f"{commit}+dirty" if changes else commit
