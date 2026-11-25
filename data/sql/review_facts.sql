CREATE VIEW review_facts AS
SELECT
    r.review_id,
    r.order_id,
    r.review_score,
    r.review_comment_title,
    r.review_comment_message,
    trim(coalesce(r.review_comment_message, '')) <> '' AS has_comment,
    r.review_creation_date::DATE AS review_date,
    r.review_answer_timestamp AS answered_at,
    date_diff('day', r.review_creation_date, r.review_answer_timestamp) AS days_to_answer,
    o.* EXCLUDE (order_id)
FROM order_reviews r
JOIN order_facts o USING (order_id)
