CREATE VIEW order_facts AS
WITH base AS (
    SELECT
        o.order_id,
        o.order_status,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,
        c.customer_zip_code_prefix,
        o.order_purchase_timestamp AS purchased_at,
        o.order_approved_at AS approved_at,
        o.order_delivered_carrier_date AS handed_to_carrier_at,
        o.order_delivered_customer_date AS delivered_at,
        o.order_estimated_delivery_date::DATE AS estimated_delivery_date
    FROM orders o
    JOIN customers c USING (customer_id)
)
SELECT
    order_id,
    order_status,
    customer_unique_id,
    customer_city,
    customer_state,
    customer_zip_code_prefix,
    purchased_at,
    purchased_at::DATE AS purchase_date,
    strftime(purchased_at, '%Y-%m') AS purchase_month,
    year(purchased_at) AS purchase_year,
    quarter(purchased_at) AS purchase_quarter,
    dayname(purchased_at) AS purchase_weekday,
    hour(purchased_at) AS purchase_hour,
    approved_at,
    handed_to_carrier_at,
    delivered_at,
    delivered_at::DATE AS delivered_date,
    estimated_delivery_date,
    date_diff('day', purchased_at, delivered_at) AS days_to_deliver,
    date_diff('day', purchased_at, estimated_delivery_date) AS days_estimated,
    date_diff('day', handed_to_carrier_at, delivered_at) AS days_carrier_to_customer,
    CASE
        WHEN order_status = 'delivered' AND delivered_at IS NOT NULL
        THEN delivered_at::DATE > estimated_delivery_date
    END AS is_late,
    row_number() OVER (
        PARTITION BY customer_unique_id ORDER BY purchased_at, order_id
    ) AS customer_order_number
FROM base
