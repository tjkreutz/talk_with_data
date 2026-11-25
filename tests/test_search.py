import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from duckdb import connect

from talk_with_data.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL
from talk_with_data.search import (
    _embed_query,
    _to_dicts,
    search_reviews,
    search_reviews_json,
)


class TestSearch(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect()
        self.connection.execute(
            "CREATE TABLE review_embeddings (review_id VARCHAR, order_id VARCHAR, "
            "review_score BIGINT, review_text VARCHAR, embedding FLOAT[])"
        )
        self.connection.execute(
            """
            INSERT INTO review_embeddings VALUES
                ('r3', 'o3', 2, 'Péssimo', [0.0, 1.0]),
                ('r1', 'o1', 5, 'Ótimo', [1.0, 0.0]),
                ('r2', 'o2', 4, 'Bom', [0.9, 0.1])
            """
        )
        self.client = MagicMock()
        self.client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(index=0, embedding=[1.0, 0.0])]
        )

    def test_search_reviews(self) -> None:
        results = search_reviews(self.connection, self.client, "excellent")

        self.assertEqual([row["review_id"] for row in results], ["r1", "r2", "r3"])
        self.assertEqual(
            results[0],
            {
                "review_id": "r1",
                "order_id": "o1",
                "review_score": 5,
                "review_text": "Ótimo",
                "similarity": 1.0,
            },
        )
        self.assertEqual(results[2]["similarity"], 0.0)
        self.assertEqual(
            self.client.embeddings.create.call_args.kwargs["input"], ["excellent"]
        )

        with patch("talk_with_data.search.SEARCH_RESULTS", 2):
            self.assertEqual(len(search_reviews(self.connection, self.client, "x")), 2)

        with self.assertRaises(ValueError):
            search_reviews(self.connection, self.client, "   ")

    def test_search_reviews_json(self) -> None:
        reply = search_reviews_json(self.connection, self.client, "excellent")

        results = json.loads(reply)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["review_text"], "Ótimo")
        self.assertIn("Ótimo", reply)

    def test_embed_query(self) -> None:
        self.assertEqual(_embed_query(self.client, "late"), [1.0, 0.0])
        call = self.client.embeddings.create.call_args.kwargs
        self.assertEqual(call["model"], EMBEDDING_MODEL)
        self.assertEqual(call["dimensions"], EMBEDDING_DIMENSIONS)
        self.assertEqual(call["input"], ["late"])

    def test_to_dicts(self) -> None:
        self.assertEqual(
            _to_dicts([("a", "INTEGER"), ("b", "VARCHAR")], [(1, "x"), (2, "y")]),
            [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}],
        )
        self.assertEqual(_to_dicts([("a", "INTEGER")], []), [])


if __name__ == "__main__":
    unittest.main()
