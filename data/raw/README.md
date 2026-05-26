# Raw Data

This folder is used to store the original Assignment 2 data files.

The required raw data files are:

```text
bus_load_2022.parquet
bus_load_2023.parquet
bus_load_2024.parquet
bus_load_2025.parquet
zone_load_2022.parquet
zone_load_2023.parquet
zone_load_2024.parquet
zone_load_2025.parquet
```

These files were provided through the Assignment 2 Google Drive folder.

Because the raw parquet files are very large, they may not be tracked directly in GitHub. To run the pipeline locally, download the files from the provided Google Drive link and place them in this folder:

```text
data/raw/
```

After placing the files here, the folder should look like this:

```text
data/raw/
├── README.md
├── bus_load_2022.parquet
├── bus_load_2023.parquet
├── bus_load_2024.parquet
├── bus_load_2025.parquet
├── zone_load_2022.parquet
├── zone_load_2023.parquet
├── zone_load_2024.parquet
└── zone_load_2025.parquet
```

The pipeline can then be run from the project root directory using:

```bash
python src/check_data.py
python src/run_pyarrow_pipeline.py --mode full
```

Note: If the parquet files are not present in this folder, the pipeline will not be able to run.
