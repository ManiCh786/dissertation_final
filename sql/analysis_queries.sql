-- KPI checks for screenshots and validation
SELECT TOP 20 * FROM customer_engagement ORDER BY engagement_score DESC;
SELECT * FROM conversion_funnel;
SELECT TOP 20 * FROM cart_abandonment ORDER BY abandonment_rate_pct DESC;
SELECT TOP 20 * FROM category_performance ORDER BY purchase_revenue DESC;

-- Total purchase revenue
SELECT SUM(purchase_revenue) AS total_purchase_revenue FROM category_performance;

-- Highest conversion categories, avoiding tiny categories
SELECT TOP 10 category_code, views, purchases, purchase_conversion_rate_pct
FROM category_performance
WHERE views >= 10
ORDER BY purchase_conversion_rate_pct DESC;
