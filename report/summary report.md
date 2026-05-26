# Summary Report

## Objective

The goal of this assignment is to build an end-to-end bus-level load prediction pipeline for next-day and next-month forecasting. The pipeline predicts hourly load demand for each bus in calendar year 2025.

## Data

The input data contains hourly bus-level and zone-level load data from 2022 to 2025. The main target variable is `pd`, which represents load demand in MW.

The bus-level data includes bus ID, bus type, base kV, zone name, load, generation, date, and hour ending. The zone-level data includes zone name, total load, total generation, bus counts, date, and hour ending.

The training period is 2022-01-01 through 2024-12-31. The test target period is 2025-01-01 through 2025-12-31.

## Pipeline Design

Because the bus-level parquet files are very large, the pipeline uses a PyArrow-based batch processing approach instead of loading the full dataset into pandas memory. This makes the workflow more scalable and avoids memory issues on a local machine.

The main steps of the pipeline are:

1. Read the 2022-2024 bus-level parquet files in batches.
2. Build historical load profiles from the training data.
3. Read the 2025 bus-level parquet file in batches.
4. Generate bus-level predictions for 2025.
5. Write next-day and next-month forecast output files.
6. Evaluate bus-level and zone-level aggregated prediction accuracy.

## Model

I used a historical profile forecasting model. The model calculates average load profiles from 2022-2024 historical data using bus ID, hour ending, and weekday.

For missing combinations, the model falls back to broader averages:

1. Bus-hour-weekday average
2. Bus-hour average
3. Bus average
4. Global hour-weekday average
5. Global average

This model is simple, interpretable, and scalable for large datasets.

## Features

The main features used by the model are:

- Bus ID
- Zone ID
- Hour ending
- Weekday
- Historical average load profile

The model mainly captures repeated daily and weekly load patterns.

## Forecast Outputs

The pipeline generates two forecast output files:

- `next_day_forecast.csv.gz`
- `next_month_forecast.csv.gz`

Both files follow the required schema:

```text
model_name
forecast_created_at
target_date
he
bus_id
zone_id
predict_pd
```

For the next-day forecast, `forecast_created_at` is set to the previous day. For example, the forecast for 2025-01-01 is created at 2024-12-31 00:01:00.

For the next-month forecast, `forecast_created_at` is set to the first day of the previous month. For example, the forecast for January 2025 is created at 2024-12-01 00:01:00.

The files are saved as `.csv.gz` because the full bus-level forecast output is very large.

## Data Leakage Prevention

To avoid data leakage, the historical load profiles are built only from 2022-2024 data. The actual 2025 load values are not used to create predictions. The 2025 data is only used after forecasting for evaluation.

This implementation uses a fixed historical profile trained on the full 2022-2024 training period for all 2025 forecasts. A more production-like implementation could rebuild the profile separately for each forecast creation date, but the current approach keeps the pipeline simple and reproducible.

## Evaluation

The output includes MAE, RMSE, and WMAPE.

The metrics are reported for:

- Next-day bus-level forecast
- Next-day zone-level aggregated forecast
- Next-month bus-level forecast
- Next-month zone-level aggregated forecast

Since the same historical profile prediction values are used for both next-day and next-month output files, the numerical accuracy values are the same in this baseline implementation. However, the forecast files use different `forecast_created_at` definitions to match the two required use cases.

The evaluation results are saved in:

```text
data/processed/metrics_summary.csv
```

The bus-level WMAPE is approximately 0.311, and the zone-level aggregated WMAPE is approximately 0.166. This shows that aggregation at the zone level reduces relative error compared with individual bus-level predictions.

## Strengths

This method has several strengths:

- It is simple and interpretable.
- It avoids loading the full dataset into memory.
- It works with very large parquet files.
- It avoids using 2025 actual load values during prediction.
- It provides both bus-level and zone-level evaluation.
- It creates forecast files with the required output schema.

## Weaknesses

This method also has limitations:

- It does not use weather data.
- It does not explicitly model holidays or unusual events.
- It does not use lag features or rolling averages.
- It does not include a machine learning model such as gradient boosting.
- It may perform poorly for buses with sparse historical data or changing load patterns.

## Future Improvements

With more time and computing resources, I would improve the pipeline by adding:

- Weather variables
- Holiday and weekend flags
- Lagged load features
- Rolling average features
- Separate next-day and next-month model strategies
- A machine learning model such as gradient boosting or random forest
- A zone forecast plus bus-share allocation strategy

I would also compare the historical profile baseline against machine learning models using sampled training data or a distributed data processing framework.

## Conclusion

This project builds a complete and reproducible bus-level load forecasting workflow for next-day and next-month use cases. The final pipeline reads large parquet files in batches, builds historical load profiles from 2022-2024 data, generates 2025 bus-level forecasts, and evaluates both bus-level and zone-level aggregated accuracy.

The current solution is a stable baseline rather than a complex machine learning model. It provides a clear starting point for large-scale load forecasting and can be improved later with additional features, weather data, and more advanced modeling methods.
