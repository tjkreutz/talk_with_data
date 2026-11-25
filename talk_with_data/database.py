from pathlib import Path

from duckdb import DuckDBPyConnection, connect

from talk_with_data.utils import load_sql

RAW_DIR = Path("data/raw")
VIEWS = ("order_facts", "review_facts")


def create_connection(raw_dir: Path = RAW_DIR) -> DuckDBPyConnection:
    connection = connect()

    for csv_path in sorted(raw_dir.glob("*.csv")):
        connection.read_csv(str(csv_path)).create(_get_table_name(csv_path))

    for view in VIEWS:
        connection.execute(load_sql(view))

    return connection


def _get_table_name(csv_path: Path) -> str:
    return csv_path.stem.removeprefix("olist_").removesuffix("_dataset")
