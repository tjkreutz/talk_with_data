import json
from time import perf_counter

from talk_with_data.config import (
    EXPERIMENT,
    EXPERIMENTS_PATH,
    QUESTIONS_DIR,
    RUNS,
    RUNS_DIR,
    SPLIT,
)
from talk_with_data.database import create_connection
from talk_with_data.experiment import (
    describe_experiment,
    run_experiment,
    write_attempts,
)
from talk_with_data.metrics import summarize
from talk_with_data.questions import load_questions
from talk_with_data.schema import describe_schema
from talk_with_data.text_to_sql import create_client
from talk_with_data.utils import append_jsonl


def main() -> None:
    connection = create_connection()
    schema = describe_schema(connection)
    started = perf_counter()
    attempts = run_experiment(
        questions=load_questions(QUESTIONS_DIR / f"{SPLIT}.jsonl"),
        client=create_client(),
        connection=connection,
        schema=schema,
        runs=RUNS,
    )
    description = describe_experiment(EXPERIMENT, SPLIT, schema)
    record = {
        **description,
        **summarize(attempts),
        "duration_seconds": round(perf_counter() - started, 1),
    }
    append_jsonl(record, EXPERIMENTS_PATH)
    write_attempts(attempts, RUNS_DIR / f"{description['id']}.jsonl")
    print(json.dumps(record, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
