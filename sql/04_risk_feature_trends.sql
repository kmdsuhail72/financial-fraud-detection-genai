-- High Risk Behavioral Anomaly Detection & Velocity Bursts
SELECT
    transaction_id,
    customer_id,
    account_id,
    merchant_category,
    amount,
    feat_amount_vs_prior_average,
    feat_transaction_count_5m_prior,
    feat_new_device_flag,
    feat_home_city_mismatch,
    location_city,
    transaction_timestamp
FROM
    finguard_data_lake_dev.transactions_silver
WHERE
    feat_amount_vs_prior_average >= 5.0
    OR feat_transaction_count_5m_prior >= 4
    OR (feat_new_device_flag = 1 AND feat_home_city_mismatch = 1)
ORDER BY
    feat_amount_vs_prior_average DESC,
    feat_transaction_count_5m_prior DESC
LIMIT 100;
