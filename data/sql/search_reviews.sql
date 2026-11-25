SELECT
    review_id,
    order_id,
    review_score,
    review_text,
    round(list_cosine_similarity(embedding, ?::FLOAT[]), 4) AS similarity
FROM review_embeddings
ORDER BY similarity DESC, review_id
LIMIT ?
