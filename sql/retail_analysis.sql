-- ============================================================
-- Online Retail Analytics — Core SQL Queries
-- Dataset: UCI Online Retail (InvoiceNo, StockCode, Quantity,
--          InvoiceDate, UnitPrice, CustomerID, Country)
-- ============================================================

-- 1. Revenue by country (top 10)
SELECT
    Country,
    COUNT(DISTINCT CustomerID)          AS unique_customers,
    COUNT(DISTINCT InvoiceNo)           AS total_orders,
    ROUND(SUM(Quantity * UnitPrice), 2) AS total_revenue
FROM retail
WHERE Quantity > 0
  AND UnitPrice > 0
  AND CustomerID IS NOT NULL
GROUP BY Country
ORDER BY total_revenue DESC
LIMIT 10;

-- 2. Monthly revenue trend
SELECT
    DATE_FORMAT(InvoiceDate, '%Y-%m')   AS month,
    ROUND(SUM(Quantity * UnitPrice), 2) AS monthly_revenue,
    COUNT(DISTINCT CustomerID)          AS active_customers
FROM retail
WHERE Quantity > 0 AND UnitPrice > 0
GROUP BY month
ORDER BY month;

-- 3. RFM segmentation using window functions
WITH rfm_base AS (
    SELECT
        CustomerID,
        DATEDIFF('2011-12-31', MAX(InvoiceDate))    AS recency_days,
        COUNT(DISTINCT InvoiceNo)                    AS frequency,
        ROUND(SUM(Quantity * UnitPrice), 2)          AS monetary
    FROM retail
    WHERE Quantity > 0
      AND UnitPrice > 0
      AND CustomerID IS NOT NULL
    GROUP BY CustomerID
),
rfm_scores AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency_days DESC)  AS r_score,
        NTILE(5) OVER (ORDER BY frequency)          AS f_score,
        NTILE(5) OVER (ORDER BY monetary)           AS m_score
    FROM rfm_base
)
SELECT
    CustomerID,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    (r_score + f_score + m_score) AS rfm_total,
    CASE
        WHEN (r_score + f_score + m_score) >= 13 THEN 'Champions'
        WHEN (r_score + f_score + m_score) >= 10 THEN 'Loyal Customers'
        WHEN (r_score + f_score + m_score) >= 7  THEN 'At Risk'
        ELSE 'Lost'
    END AS segment
FROM rfm_scores
ORDER BY rfm_total DESC;

-- 4. Product performance (top 20 by revenue)
SELECT
    StockCode,
    Description,
    SUM(Quantity)                       AS units_sold,
    ROUND(SUM(Quantity * UnitPrice), 2) AS revenue,
    COUNT(DISTINCT InvoiceNo)           AS order_count
FROM retail
WHERE Quantity > 0 AND UnitPrice > 0
GROUP BY StockCode, Description
ORDER BY revenue DESC
LIMIT 20;

-- 5. Customer repeat purchase rate
WITH order_counts AS (
    SELECT
        CustomerID,
        COUNT(DISTINCT InvoiceNo) AS num_orders
    FROM retail
    WHERE CustomerID IS NOT NULL AND Quantity > 0
    GROUP BY CustomerID
)
SELECT
    ROUND(100.0 * SUM(CASE WHEN num_orders > 1 THEN 1 ELSE 0 END)
          / COUNT(*), 2)             AS repeat_purchase_rate_pct,
    ROUND(AVG(num_orders), 2)        AS avg_orders_per_customer,
    MAX(num_orders)                  AS max_orders_single_customer
FROM order_counts;

-- 6. Revenue contribution by customer segment (post-RFM)
WITH rfm_segments AS (
    SELECT
        CustomerID,
        ROUND(SUM(Quantity * UnitPrice), 2) AS monetary,
        CASE
            WHEN NTILE(3) OVER (ORDER BY SUM(Quantity * UnitPrice) DESC) = 1 THEN 'High Value'
            WHEN NTILE(3) OVER (ORDER BY SUM(Quantity * UnitPrice) DESC) = 2 THEN 'Mid Value'
            ELSE 'Low Value'
        END AS value_segment
    FROM retail
    WHERE Quantity > 0 AND UnitPrice > 0 AND CustomerID IS NOT NULL
    GROUP BY CustomerID
)
SELECT
    value_segment,
    COUNT(*)                            AS customer_count,
    ROUND(SUM(monetary), 2)            AS total_revenue,
    ROUND(AVG(monetary), 2)            AS avg_revenue_per_customer,
    ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS pct_of_total_revenue
FROM rfm_segments
GROUP BY value_segment
ORDER BY total_revenue DESC;
