import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Question:
    id: str
    template: str
    question: str
    gold_sql: str


def load_questions(path: Path) -> list[Question]:
    with path.open(encoding="utf-8") as file:
        return [Question(**json.loads(line)) for line in file if line.strip()]
