-- Payment Channel Breakdown and Risk Exposure
SELECT
    channel,
    COUNT(transaction_id) AS transaction_count,
    ROUND(SUM(amount), 2) AS total_volume_inr,
    ROUND(AVG(amount), 2) AS average_amount,
    SUM(feat_new_device_flag) AS total_unseen_devices,
    ROUND(CAST(SUM(feat_new_device_flag) AS DOUBLE) / COUNT(transaction_id) * 100, 2) AS pct_new_device,
    SUM(feat_is_international) AS total_cross_border,
    ROUND(CAST(SUM(feat_is_international) AS DOUBLE) / COUNT(transaction_id) * 100, 2) AS pct_cross_border
FROM
    finguard_data_lake_dev.transactions_silver
GROUP BY
    channel
ORDER BY
    total_volume_inr DESC;
