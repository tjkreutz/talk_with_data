from pathlib import Path

MODEL = "google/gemini-3.5-flash-lite"
PROMPT_NAME = "text_to_sql_prompt"

WRITER_MODEL = "meta-llama/llama-3.1-8b-instruct"
WRITER_PROMPT_NAME = "writer_prompt"
WRITER_TEMPERATURE = 0
WRITER_MAX_ROWS = 20

EMBEDDING_MODEL = "mongodb/voyage-4-lite"
EMBEDDING_DIMENSIONS = 256
SEARCH_RESULTS = 10
MAX_TOOL_ROUNDS = 3
HISTORY_TURNS = 5

RAW_DIR = Path("data/raw")
SQL_DIR = Path("data/sql")
PROMPT_DIR = Path("data/prompts")
QUESTIONS_DIR = Path("data/questions")
EXPERIMENTS_PATH = Path("data/experiments.jsonl")
RUNS_DIR = Path("data/runs")
VECTORS_PATH = Path("data/vectors/review_embeddings.parquet")

VIEWS = ("order_facts", "review_facts")

EXPERIMENT = "baseline"
SPLIT = "dev"
RUNS = 5
MAX_WORKERS = 8
PREVIEW_ROWS = 5
HASH_LENGTH = 8

RESAMPLES = 1000
CONFIDENCE = 0.95
DECIMALS = 3
SEED = 42
