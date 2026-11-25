import json
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from subprocess import run

SQL_DIR = Path("data/sql")
PROMPT_DIR = Path("data/prompts")


def load_sql(name: str, sql_dir: Path = SQL_DIR) -> str:
    return (sql_dir / f"{name}.sql").read_text(encoding="utf-8")


def load_prompt(name: str, prompt_dir: Path = PROMPT_DIR) -> str:
    return (prompt_dir / f"{name}.txt").read_text(encoding="utf-8")


def append_jsonl(row: Mapping[str, object], path: Path) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(f"{json.dumps(row, ensure_ascii=False)}\n")


def write_jsonl(rows: Iterable[Mapping[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = (json.dumps(row, ensure_ascii=False, default=str) for row in rows)
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def group_by[Item, Key](
    items: Iterable[Item], key: Callable[[Item], Key]
) -> dict[Key, list[Item]]:
    groups: dict[Key, list[Item]] = {}

    for item in items:
        groups.setdefault(key(item), []).append(item)

    return groups


def get_git_version() -> str:
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
