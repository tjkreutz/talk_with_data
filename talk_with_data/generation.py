import os
import re

from dotenv import load_dotenv
from openai import OpenAI

MODEL = "anthropic/claude-haiku-5.5"
SYSTEM_PROMPT = """You write DuckDB SQL queries for a database with this schema:

{schema}

Answer the user's question with a single SQL query inside a ```sql code block. Do not explain."""
CODE_BLOCK = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL)


def generate_sql(client: OpenAI, question: str, schema: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(schema=schema)},
            {"role": "user", "content": question},
        ],
    )

    return extract_sql(response.choices[0].message.content or "")


def create_client() -> OpenAI:
    load_dotenv()

    return OpenAI(base_url=os.environ["LLM_API_URL"], api_key=os.environ["LLM_API_KEY"])


def extract_sql(reply: str) -> str:
    match = CODE_BLOCK.search(reply)

    return (match.group(1) if match else reply).strip()
