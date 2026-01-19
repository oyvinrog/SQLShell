# Test Data Generator

Generate large CSV datasets for SQLShell performance testing. The generator writes
rows incrementally so you can create huge files without holding data in memory.

## Usage

```bash
python -m sqlshell.utils.testdata.generate_testdata \
  --rows 1000000 \
  --cols a,b,c \
  --data_types int,float,str \
  --lov_a 1,2,3 \
  --lov_b 1.2,3.4 \
  --lov_c man,cow,woman \
  --output /tmp/bigdata.csv
```

### Parquet output

```bash
python -m sqlshell.utils.testdata.generate_testdata \
  --rows 1000000 \
  --cols id,amount,category \
  --data_types int,float,str \
  --format parquet \
  --compression snappy \
  --output /tmp/bigdata.parquet
```

### Common options

- `--rows`: Number of rows to generate (required).
- `--cols`: Comma-separated column names (required).
- `--data_types`: Comma-separated column types (`int`, `float`, `str`).
  If you pass a single type it will be applied to all columns.
- `--output`: Output file path or `-` for stdout (CSV only).
- `--format`: `csv` (default) or `parquet`.
- `--compression`: Parquet compression codec (default: `snappy`).
- `--seed`: Random seed for reproducible output.
- `--delimiter`: CSV delimiter.
- `--chunk-size`: Rows per batch; larger values are faster but use more memory.

### Type tuning options

- `--int-min`, `--int-max`
- `--float-min`, `--float-max`, `--float-precision`
- `--str-min-len`, `--str-max-len`

### List-of-values

Use `--lov_<column>` to constrain values for a column.

```bash
python -m sqlshell.utils.testdata.generate_testdata \
  --rows 1000 \
  --cols status,price,category \
  --data_types str,float,str \
  --lov_status open,closed,pending \
  --lov_category consumer,enterprise \
  --output testdata.csv
```

### Performance tips

- Increase `--chunk-size` to reduce overhead (e.g. `50000` or `100000`).
- Prefer `int`/`float` with ranges or LoV lists when possible; random strings are slower.
