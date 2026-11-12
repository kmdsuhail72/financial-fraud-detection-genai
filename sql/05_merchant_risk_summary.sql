-- Merchant Category Risk and Spending Distribution
SELECT
    merchant_category,
    COUNT(transaction_id) AS total_transactions,
    ROUND(SUM(amount), 2) AS total_spend_inr,
    ROUND(AVG(amount), 2) AS avg_transaction_size,
    SUM(CASE WHEN feat_amount_vs_prior_average > 4.0 THEN 1 ELSE 0 END) AS surge_transactions,
    ROUND(CAST(SUM(CASE WHEN feat_amount_vs_prior_average > 4.0 THEN 1 ELSE 0 END) AS DOUBLE) / COUNT(transaction_id) * 100, 2) AS surge_pct
FROM
    finguard_data_lake_dev.transactions_silver
GROUP BY
    merchant_category
ORDER BY
    surge_transactions DESC, total_spend_inr DESC;

