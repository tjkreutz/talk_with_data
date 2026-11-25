from pathlib import Path

from duckdb import DuckDBPyConnection, connect

RAW_DIR = Path("data/raw")


def create_connection(raw_dir: Path = RAW_DIR) -> DuckDBPyConnection:
    connection = connect()

    for csv_path in sorted(raw_dir.glob("*.csv")):
        connection.read_csv(str(csv_path)).create(get_table_name(csv_path))

    return connection


def get_table_name(csv_path: Path) -> str:
    return csv_path.stem.removeprefix("olist_").removesuffix("_dataset")
