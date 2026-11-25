import tempfile
import unittest
from pathlib import Path

from talk_with_data.database import create_connection, get_table_name

ORDERS_CSV = (
    '"order_id","order_purchase_timestamp"\n'
    '"a1","2017-11-24 10:00:00"\n'
    '"a2","2018-01-02 08:30:00"\n'
)
CUSTOMERS_CSV = '"customer_id","customer_zip_code_prefix"\n"c1","01003"\n"c2","14409"\n'
TRANSLATION_CSV = (
    "\ufeffproduct_category_name,product_category_name_english\nbeleza,beauty\n"
)


class TestDatabase(unittest.TestCase):
    def test_create_connection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory)
            (raw_dir / "olist_orders_dataset.csv").write_text(ORDERS_CSV)
            (raw_dir / "olist_customers_dataset.csv").write_text(CUSTOMERS_CSV)
            (raw_dir / "product_category_name_translation.csv").write_text(
                TRANSLATION_CSV, encoding="utf-8"
            )
            (raw_dir / "notes.txt").write_text("not a table")

            connection = create_connection(raw_dir=raw_dir)

        tables = connection.sql("SELECT table_name FROM information_schema.tables")
        self.assertEqual(
            {name for (name,) in tables.fetchall()},
            {"orders", "customers", "product_category_name_translation"},
        )
        self.assertEqual(
            connection.sql("SELECT count(*) FROM orders").fetchall(), [(2,)]
        )
        self.assertEqual(
            connection.sql(
                "SELECT customer_zip_code_prefix FROM customers ORDER BY 1"
            ).fetchall(),
            [("01003",), ("14409",)],
        )
        self.assertEqual(
            connection.sql("SELECT typeof(order_purchase_timestamp) FROM orders")
            .limit(1)
            .fetchall(),
            [("TIMESTAMP",)],
        )
        self.assertEqual(
            connection.sql(
                "SELECT product_category_name_english FROM product_category_name_translation"
            ).fetchall(),
            [("beauty",)],
        )

    def test_get_table_name(self) -> None:
        self.assertEqual(
            get_table_name(Path("data/raw/olist_orders_dataset.csv")), "orders"
        )
        self.assertEqual(
            get_table_name(Path("olist_order_items_dataset.csv")), "order_items"
        )
        self.assertEqual(
            get_table_name(Path("product_category_name_translation.csv")),
            "product_category_name_translation",
        )


if __name__ == "__main__":
    unittest.main()
