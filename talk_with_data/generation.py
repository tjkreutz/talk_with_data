import os
import re

from dotenv import load_dotenv
from openai import OpenAI

from talk_with_data.utils import load_prompt

MODEL = "google/gemini-3.5-flash-lite"
CODE_BLOCK = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL)


def generate_sql(client: OpenAI, question: str, schema: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": build_system_prompt(schema)},
            {"role": "user", "content": question},
        ],
    )

    return _extract_sql(response.choices[0].message.content or "")


def build_system_prompt(schema: str) -> str:
    return load_prompt("system_prompt").format(schema=schema)


def create_client() -> OpenAI:
    load_dotenv()

    return OpenAI(base_url=os.environ["LLM_API_URL"], api_key=os.environ["LLM_API_KEY"])


def _extract_sql(reply: str) -> str:
    match = CODE_BLOCK.search(reply)

    return (match.group(1) if match else reply).strip()
