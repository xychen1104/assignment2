# Assignment 2: Bus-level Load Prediction Pipeline

This repository contains a lightweight solution for Assignment 2. The original dataset is very large, so this version avoids loading all parquet files into memory at once.

## How to run

First check that Python works and pyarrow can be imported:

```bash
python -c "import pyarrow; print('pyarrow ok')"
```

Check the data files:

```bash
python src/check_data.py
```

Run a quick test first:

```bash
python src/run_pyarrow_pipeline.py --mode quick
```

Then run the full pipeline:

```bash
python src/run_pyarrow_pipeline.py --mode full
```

## Outputs

The pipeline writes:

- `data/processed/next_day_forecast.csv.gz`
- `data/processed/next_month_forecast.csv.gz`
- `data/processed/metrics_summary.csv`

The forecast files follow the required schema:

- `model_name`
- `forecast_created_at`
- `target_date`
- `he`
- `bus_id`
- `zone_id`
- `predict_pd`

## Method

The model is a historical profile baseline. It uses 2022-2024 historical bus load data and creates average load profiles by bus, hour ending, and weekday. If a specific bus-hour-weekday profile is unavailable, it falls back to bus-hour average, bus average, global hour-weekday average, and then global average.

This approach is simple, reproducible, and avoids future data leakage because 2025 target load is only used for evaluation.
