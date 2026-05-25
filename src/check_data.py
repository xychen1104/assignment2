from pathlib import Path
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / 'data' / 'raw'

print('Project root:', ROOT)
print('Raw data directory:', RAW_DIR)

if not RAW_DIR.exists():
    raise FileNotFoundError(f'Raw data folder not found: {RAW_DIR}')

files = sorted(RAW_DIR.glob('*.parquet'))
if not files:
    raise FileNotFoundError(f'No parquet files found in {RAW_DIR}')

for path in files:
    pf = pq.ParquetFile(path)
    print('\nFile:', path.name)
    print('Rows:', pf.metadata.num_rows)
    print('Columns:', pf.schema_arrow.names)

print('\nData check finished.')
