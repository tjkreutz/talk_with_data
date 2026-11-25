from talk_with_data import (
    answer_question,
    create_client,
    create_connection,
    describe_schema,
)

PROMPT = "Question (empty line to quit): "


def main() -> None:
    connection = create_connection()
    client = create_client()
    schema = describe_schema(connection)
    history: list[tuple[str, str]] = []

    while question := _read_question():
        answer = answer_question(connection, client, schema, question, history)
        print(answer.text)

        if answer.error is None:
            history.append((question, answer.sql))


def _read_question() -> str:
    try:
        return input(PROMPT).strip()
    except (EOFError, KeyboardInterrupt):
        return ""


if __name__ == "__main__":
    main()
