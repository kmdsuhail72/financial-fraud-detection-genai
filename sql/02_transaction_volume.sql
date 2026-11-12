-- Daily Transaction Volume and Spend Analysis
SELECT
    year,
    month,
    day,
    COUNT(transaction_id) AS total_transactions,
    ROUND(SUM(amount), 2) AS total_volume_inr,
    ROUND(AVG(amount), 2) AS average_ticket_size_inr,
    ROUND(MIN(amount), 2) AS min_amount,
    ROUND(MAX(amount), 2) AS max_amount,
    COUNT(DISTINCT customer_id) AS unique_active_customers,
    COUNT(DISTINCT account_id) AS unique_active_accounts
FROM
    finguard_data_lake_dev.transactions_silver
GROUP BY
    year, month, day
ORDER BY
    year DESC, month DESC, day DESC;

