CREATE OR REPLACE TABLE review_embeddings AS
SELECT review_id, order_id, review_score, review_text, embedding::FLOAT[] AS embedding
FROM read_parquet(?)
