from pathlib import Path
from collections import defaultdict
from datetime import date, datetime, timedelta
import argparse
import csv
import gzip
import math
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / 'data' / 'raw'
PROCESSED_DIR = ROOT / 'data' / 'processed'
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = 'historical_profile_pyarrow'
TRAIN_YEARS = [2022, 2023, 2024]
TEST_YEAR = 2025
BATCH_SIZE = 250_000


def find_file(prefix: str, year: int) -> Path:
    matches = sorted(RAW_DIR.glob(f'{prefix}_{year}.parquet'))
    if not matches:
        matches = sorted(RAW_DIR.glob(f'*{prefix}*{year}*.parquet'))
    if not matches:
        raise FileNotFoundError(f'Could not find {prefix}_{year}.parquet in {RAW_DIR}')
    return matches[0]


def parse_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        raise ValueError('date value is None')
    s = str(value)[:10]
    return datetime.strptime(s, '%Y-%m-%d').date()


def previous_month_first_day(d: date) -> date:
    first = d.replace(day=1)
    prev_last = first - timedelta(days=1)
    return prev_last.replace(day=1)


def add_stat(stats, key, value):
    s, c = stats.get(key, (0.0, 0))
    stats[key] = (s + float(value), c + 1)


def mean_from_stats(stats, key):
    item = stats.get(key)
    if not item:
        return None
    s, c = item
    if c == 0:
        return None
    return s / c


def build_historical_profile(mode: str):
    exact = {}       # (bus_id, he, weekday) -> mean pd
    bus_hour = {}    # (bus_id, he) -> mean pd
    bus_avg = {}     # bus_id -> mean pd
    global_hd = {}   # (he, weekday) -> mean pd
    global_h = {}    # he -> mean pd
    global_all = {'sum': 0.0, 'count': 0}

    max_batches = 2 if mode == 'quick' else None

    print('Step 1: Building historical profile from 2022-2024 bus data')
    for year in TRAIN_YEARS:
        path = find_file('bus_load', year)
        pf = pq.ParquetFile(path)
        schema_cols = set(pf.schema_arrow.names)
        columns = ['bus_unique_id', 'zone_name', 'pd', 'date', 'he']
        if 'bus_type' in schema_cols:
            columns.append('bus_type')
        print(f'  Reading {path.name} ...')

        batch_count = 0
        row_count = 0
        used_count = 0
        for batch in pf.iter_batches(batch_size=BATCH_SIZE, columns=columns):
            data = batch.to_pydict()
            n = len(data['pd'])
            row_count += n
            batch_count += 1

            bus_types = data.get('bus_type')
            for i in range(n):
                if bus_types is not None:
                    bt = bus_types[i]
                    if bt is not None and str(bt).upper() != 'LOAD':
                        continue
                pd_val = data['pd'][i]
                if pd_val is None:
                    continue
                try:
                    pd_float = float(pd_val)
                except Exception:
                    continue
                if math.isnan(pd_float):
                    continue

                bus_id = str(data['bus_unique_id'][i])
                he = int(data['he'][i])
                d = parse_date(data['date'][i])
                weekday = d.weekday()

                add_stat(exact, (bus_id, he, weekday), pd_float)
                add_stat(bus_hour, (bus_id, he), pd_float)
                add_stat(bus_avg, bus_id, pd_float)
                add_stat(global_hd, (he, weekday), pd_float)
                add_stat(global_h, he, pd_float)
                global_all['sum'] += pd_float
                global_all['count'] += 1
                used_count += 1

            if max_batches is not None and batch_count >= max_batches:
                break

        print(f'    scanned rows: {row_count:,}; used rows with pd: {used_count:,}; batches: {batch_count}')
        if mode == 'quick':
            print('    quick mode: stopping after a few batches for testing')
            break

    global_mean = global_all['sum'] / max(global_all['count'], 1)
    print('Historical profile ready.')
    print(f'  exact groups: {len(exact):,}')
    print(f'  bus-hour groups: {len(bus_hour):,}')
    print(f'  bus groups: {len(bus_avg):,}')
    print(f'  global mean: {global_mean:.4f}')
    return exact, bus_hour, bus_avg, global_hd, global_h, global_mean


def predict_pd(bus_id, he, weekday, profile):
    exact, bus_hour, bus_avg, global_hd, global_h, global_mean = profile
    pred = mean_from_stats(exact, (bus_id, he, weekday))
    if pred is None:
        pred = mean_from_stats(bus_hour, (bus_id, he))
    if pred is None:
        pred = mean_from_stats(bus_avg, bus_id)
    if pred is None:
        pred = mean_from_stats(global_hd, (he, weekday))
    if pred is None:
        pred = mean_from_stats(global_h, he)
    if pred is None:
        pred = global_mean
    return max(float(pred), 0.0)


def init_metric():
    return {'sum_abs': 0.0, 'sum_sq': 0.0, 'sum_actual_abs': 0.0, 'count': 0}


def update_metric(m, actual, pred):
    err = float(actual) - float(pred)
    m['sum_abs'] += abs(err)
    m['sum_sq'] += err * err
    m['sum_actual_abs'] += abs(float(actual))
    m['count'] += 1


def finalize_metric(name, m, task):
    count = max(m['count'], 1)
    return {
        'task': task,
        'model_name': name,
        'MAE': m['sum_abs'] / count,
        'RMSE': math.sqrt(m['sum_sq'] / count),
        'WMAPE': m['sum_abs'] / m['sum_actual_abs'] if m['sum_actual_abs'] else None,
        'row_count': m['count'],
    }


def write_metrics(rows):
    out_path = PROCESSED_DIR / 'metrics_summary.csv'
    with out_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['task', 'model_name', 'MAE', 'RMSE', 'WMAPE', 'row_count'])
        writer.writeheader()
        writer.writerows(rows)
    print('Wrote', out_path)


def forecast_2025(profile, mode: str):
    print('Step 2: Forecasting 2025 bus-level load')
    path = find_file('bus_load', TEST_YEAR)
    pf = pq.ParquetFile(path)
    schema_cols = set(pf.schema_arrow.names)
    columns = ['bus_unique_id', 'zone_name', 'pd', 'date', 'he']
    if 'bus_type' in schema_cols:
        columns.append('bus_type')

    max_batches = 2 if mode == 'quick' else None

    next_day_path = PROCESSED_DIR / 'next_day_forecast.csv.gz'
    next_month_path = PROCESSED_DIR / 'next_month_forecast.csv.gz'

    bus_metric = init_metric()
    zone_actual_pred = defaultdict(lambda: [0.0, 0.0])  # (date, he, zone) -> actual_sum, pred_sum

    with gzip.open(next_day_path, 'wt', newline='', encoding='utf-8') as f_day, \
         gzip.open(next_month_path, 'wt', newline='', encoding='utf-8') as f_month:
        fieldnames = ['model_name', 'forecast_created_at', 'target_date', 'he', 'bus_id', 'zone_id', 'predict_pd']
        day_writer = csv.DictWriter(f_day, fieldnames=fieldnames)
        month_writer = csv.DictWriter(f_month, fieldnames=fieldnames)
        day_writer.writeheader()
        month_writer.writeheader()

        batch_count = 0
        written = 0
        for batch in pf.iter_batches(batch_size=BATCH_SIZE, columns=columns):
            data = batch.to_pydict()
            n = len(data['he'])
            batch_count += 1
            bus_types = data.get('bus_type')

            for i in range(n):
                if bus_types is not None:
                    bt = bus_types[i]
                    if bt is not None and str(bt).upper() != 'LOAD':
                        continue

                d = parse_date(data['date'][i])
                he = int(data['he'][i])
                bus_id = str(data['bus_unique_id'][i])
                zone_id = str(data['zone_name'][i])
                weekday = d.weekday()
                pred = predict_pd(bus_id, he, weekday, profile)

                target_date = d.isoformat()
                row_day = {
                    'model_name': MODEL_NAME,
                    'forecast_created_at': (d - timedelta(days=1)).isoformat() + ' 00:01:00',
                    'target_date': target_date,
                    'he': he,
                    'bus_id': bus_id,
                    'zone_id': zone_id,
                    'predict_pd': f'{pred:.6f}',
                }
                row_month = dict(row_day)
                row_month['forecast_created_at'] = previous_month_first_day(d).isoformat() + ' 00:01:00'

                day_writer.writerow(row_day)
                month_writer.writerow(row_month)
                written += 1

                actual = data['pd'][i]
                if actual is not None:
                    try:
                        actual_f = float(actual)
                        if not math.isnan(actual_f):
                            update_metric(bus_metric, actual_f, pred)
                            zkey = (target_date, he, zone_id)
                            zone_actual_pred[zkey][0] += actual_f
                            zone_actual_pred[zkey][1] += pred
                    except Exception:
                        pass

            print(f'  processed batch {batch_count}; total forecast rows written: {written:,}')
            if max_batches is not None and batch_count >= max_batches:
                print('  quick mode: stopping after a few batches for testing')
                break

    zone_metric = init_metric()
    for actual_sum, pred_sum in zone_actual_pred.values():
        update_metric(zone_metric, actual_sum, pred_sum)

    metrics = [
        finalize_metric(MODEL_NAME, bus_metric, 'bus_level_2025'),
        finalize_metric(MODEL_NAME, zone_metric, 'zone_aggregated_2025'),
    ]
    write_metrics(metrics)

    print('Wrote', next_day_path)
    print('Wrote', next_month_path)
    print('Step 3: Pipeline finished.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['quick', 'full'], default='quick')
    args = parser.parse_args()

    print('Running pyarrow-only lightweight pipeline')
    print('Mode:', args.mode)
    print('This version does not import pandas, sklearn, or duckdb.')

    profile = build_historical_profile(args.mode)
    forecast_2025(profile, args.mode)


if __name__ == '__main__':
    main()
