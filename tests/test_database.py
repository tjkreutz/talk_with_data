import tempfile
import unittest
from pathlib import Path

from duckdb import DuckDBPyConnection

from talk_with_data.database import _get_table_name, create_connection

ORDERS_CSV = """order_id,customer_id,order_status,order_purchase_timestamp,order_approved_at,order_delivered_carrier_date,order_delivered_customer_date,order_estimated_delivery_date
o1,c1,delivered,2017-11-24 10:00:00,2017-11-24 11:00:00,2017-11-25 09:00:00,2017-12-05 23:30:00,2017-12-05 00:00:00
o2,c2,delivered,2018-01-02 08:30:00,2018-01-02 09:00:00,2018-01-03 08:00:00,2018-01-20 09:00:00,2018-01-10 00:00:00
o3,c3,canceled,2018-01-03 12:00:00,2018-01-03 12:30:00,,2018-02-01 09:00:00,2018-01-10 00:00:00
o4,c4,shipped,2018-01-02 08:30:00,2018-01-02 09:00:00,,,2018-01-10 00:00:00
"""
CUSTOMERS_CSV = """customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state
c1,u1,01003,sao paulo,SP
c2,u1,14409,franca,SP
c3,u2,20000,rio de janeiro,RJ
c4,u1,01003,sao paulo,SP
"""
REVIEWS_CSV = (
    "review_id,order_id,review_score,review_comment_title,review_comment_message,review_creation_date,review_answer_timestamp\n"
    "r1,o1,5,,Great,2017-12-06 00:00:00,2017-12-08 15:00:00\n"
    'r2,o2,1,,"   ",2018-01-21 00:00:00,2018-01-21 10:00:00\n'
    "r3,o2,2,,,2018-01-21 00:00:00,2018-01-23 12:00:00\n"
)
TRANSLATION_CSV = "﻿product_category_name,product_category_name_english\nbeleza,beauty\n"


def _write_raw_files(raw_dir: Path) -> None:
    (raw_dir / "olist_orders_dataset.csv").write_text(ORDERS_CSV)
    (raw_dir / "olist_customers_dataset.csv").write_text(CUSTOMERS_CSV)
    (raw_dir / "olist_order_reviews_dataset.csv").write_text(REVIEWS_CSV)
    (raw_dir / "product_category_name_translation.csv").write_text(
        TRANSLATION_CSV, encoding="utf-8"
    )
    (raw_dir / "notes.txt").write_text("not a table")


class TestDatabase(unittest.TestCase):
    def setUp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _write_raw_files(Path(directory))
            self.connection: DuckDBPyConnection = create_connection(
                raw_dir=Path(directory)
            )

    def test_create_connection(self) -> None:
        tables = self.connection.sql("SELECT table_name FROM information_schema.tables")

        self.assertEqual(
            {name for (name,) in tables.fetchall()},
            {
                "orders",
                "customers",
                "order_reviews",
                "product_category_name_translation",
                "order_facts",
                "review_facts",
            },
        )
        self.assertEqual(
            self.connection.sql("SELECT count(*) FROM orders").fetchall(), [(4,)]
        )
        self.assertEqual(
            self.connection.sql(
                "SELECT customer_zip_code_prefix FROM customers ORDER BY 1"
            ).fetchall(),
            [("01003",), ("01003",), ("14409",), ("20000",)],
        )
        self.assertEqual(
            self.connection.sql("SELECT typeof(order_purchase_timestamp) FROM orders")
            .limit(1)
            .fetchall(),
            [("TIMESTAMP",)],
        )
        self.assertEqual(
            self.connection.sql(
                "SELECT product_category_name_english FROM product_category_name_translation"
            ).fetchall(),
            [("beauty",)],
        )

    def test_order_facts(self) -> None:
        facts = self.connection.sql(
            """
            SELECT order_id, customer_unique_id, customer_state, purchase_month,
                   days_to_deliver, days_estimated, days_carrier_to_customer,
                   is_late, customer_order_number
            FROM order_facts ORDER BY order_id
            """
        ).fetchall()

        self.assertEqual(
            facts,
            [
                ("o1", "u1", "SP", "2017-11", 11, 11, 10, False, 1),
                ("o2", "u1", "SP", "2018-01", 18, 8, 17, True, 2),
                ("o3", "u2", "RJ", "2018-01", 29, 7, None, None, 1),
                ("o4", "u1", "SP", "2018-01", None, 8, None, None, 3),
            ],
        )
        self.assertEqual(
            self.connection.sql(
                "SELECT typeof(estimated_delivery_date), typeof(delivered_date) FROM order_facts LIMIT 1"
            ).fetchall(),
            [("DATE", "DATE")],
        )
        self.assertEqual(
            self.connection.sql(
                "SELECT customer_zip_code_prefix FROM order_facts WHERE order_id = 'o1'"
            ).fetchall(),
            [("01003",)],
        )
        self.assertEqual(
            self.connection.sql(
                "SELECT purchase_year, purchase_quarter, purchase_weekday, purchase_hour "
                "FROM order_facts WHERE order_id = 'o1'"
            ).fetchall(),
            [(2017, 4, "Friday", 10)],
        )

    def test_review_facts(self) -> None:
        facts = self.connection.sql(
            """
            SELECT review_id, has_comment, days_to_answer, is_late, customer_state,
                   purchase_month
            FROM review_facts ORDER BY review_id
            """
        ).fetchall()

        self.assertEqual(
            facts,
            [
                ("r1", True, 2, False, "SP", "2017-11"),
                ("r2", False, 0, True, "SP", "2018-01"),
                ("r3", False, 2, True, "SP", "2018-01"),
            ],
        )
        self.assertEqual(
            self.connection.sql("SELECT count(*) FROM review_facts").fetchall(),
            self.connection.sql("SELECT count(*) FROM order_reviews").fetchall(),
        )

    def test_get_table_name(self) -> None:
        self.assertEqual(
            _get_table_name(Path("data/raw/olist_orders_dataset.csv")), "orders"
        )
        self.assertEqual(
            _get_table_name(Path("olist_order_items_dataset.csv")), "order_items"
        )
        self.assertEqual(
            _get_table_name(Path("product_category_name_translation.csv")),
            "product_category_name_translation",
        )


if __name__ == "__main__":
    unittest.main()
