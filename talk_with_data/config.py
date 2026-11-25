from pathlib import Path

MODEL = "google/gemini-3.5-flash-lite"
PROMPT_NAME = "system_prompt"

RAW_DIR = Path("data/raw")
SQL_DIR = Path("data/sql")
PROMPT_DIR = Path("data/prompts")
QUESTIONS_DIR = Path("data/questions")
EXPERIMENTS_PATH = Path("data/experiments.jsonl")
RUNS_DIR = Path("data/runs")

VIEWS = ("order_facts", "review_facts")
MODEL_TABLES = VIEWS

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
