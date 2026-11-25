from talk_with_data.answer import answer_question
from talk_with_data.database import create_connection
from talk_with_data.schema import describe_schema
from talk_with_data.text_to_sql import create_client

PROMPT = "Question (empty line to quit): "


def main() -> None:
    connection = create_connection()
    client = create_client()
    schema = describe_schema(connection)

    while question := _read_question():
        print(answer_question(connection, client, schema, question).text)


def _read_question() -> str:
    try:
        return input(PROMPT).strip()
    except (EOFError, KeyboardInterrupt):
        return ""


if __name__ == "__main__":
    main()
