#!/usr/bin/env python3
import argparse
import csv
import random
import string
import sys
import time
from typing import Callable, Dict, Iterable, List, Optional, Tuple

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional acceleration
    np = None


def parse_list(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_lov_args(argv: List[str]) -> Tuple[Dict[str, List[str]], List[str]]:
    lovs: Dict[str, List[str]] = {}
    remaining: List[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if not arg.startswith("--lov_"):
            remaining.append(arg)
            i += 1
            continue
        key = arg[len("--lov_"):]
        if "=" in key:
            key, value = key.split("=", 1)
        else:
            i += 1
            if i >= len(argv):
                raise SystemExit(f"Missing value for --lov_{key}")
            value = argv[i]
        lovs[key] = parse_list(value)
        i += 1
    return lovs, remaining


def build_generators(
    cols: List[str],
    types: List[str],
    lovs: Dict[str, List[str]],
    int_min: int,
    int_max: int,
    float_min: float,
    float_max: float,
    float_precision: int,
    str_min_len: int,
    str_max_len: int,
) -> List[Callable[[int], List[object]]]:
    generators: List[Callable[[int], List[object]]] = []
    alphabet = string.ascii_letters + string.digits
    rng = np.random.default_rng() if np is not None else None

    for col, col_type in zip(cols, types):
        lov = lovs.get(col)
        if lov:
            if col_type == "int":
                parsed = [int(v) for v in lov]
            elif col_type == "float":
                parsed = [float(v) for v in lov]
            else:
                parsed = lov

            def make_choice(values: List[object]):
                if rng is not None:
                    return lambda n: rng.choice(values, size=n).tolist()
                return lambda n: [random.choice(values) for _ in range(n)]

            generators.append(make_choice(parsed))
            continue

        if col_type == "int":
            if rng is not None:
                generators.append(
                    lambda n: rng.integers(int_min, int_max + 1, size=n).tolist()
                )
            else:
                generators.append(
                    lambda n: [random.randint(int_min, int_max) for _ in range(n)]
                )
        elif col_type == "float":
            if rng is not None:
                def make_floats(n: int) -> List[object]:
                    values = rng.uniform(float_min, float_max, size=n)
                    if float_precision >= 0:
                        values = np.round(values, float_precision)
                    return values.tolist()

                generators.append(make_floats)
            else:
                generators.append(
                    lambda n: [
                        round(random.uniform(float_min, float_max), float_precision)
                        for _ in range(n)
                    ]
                )
        else:
            def make_random_text(n: int) -> List[object]:
                choices = random.choices
                if rng is not None:
                    lengths = rng.integers(str_min_len, str_max_len + 1, size=n)
                else:
                    lengths = [random.randint(str_min_len, str_max_len) for _ in range(n)]
                return ["".join(choices(alphabet, k=int(length))) for length in lengths]

            generators.append(make_random_text)

    return generators


def generate_rows(
    row_count: int,
    generators: List[Callable[[int], List[object]]],
    chunk_size: int,
) -> Iterable[List[object]]:
    remaining = row_count
    while remaining > 0:
        batch = min(chunk_size, remaining)
        columns = [gen(batch) for gen in generators]
        for row in zip(*columns):
            yield row
        remaining -= batch


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds:.2f}s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, seconds = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m{seconds:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate large CSV datasets with custom columns and types."
    )
    parser.add_argument("--rows", type=int, required=True, help="Number of rows to emit.")
    parser.add_argument(
        "--cols",
        required=True,
        help="Comma-separated column names (example: a,b,c).",
    )
    parser.add_argument(
        "--data_types",
        default="str",
        help="Comma-separated column types (int,float,str). Defaults to str.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path or '-' for stdout (CSV only).",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "parquet"],
        default="csv",
        help="Output format.",
    )
    parser.add_argument(
        "--compression",
        default="snappy",
        help="Parquet compression codec (ignored for CSV).",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed.")
    parser.add_argument("--delimiter", default=",", help="CSV delimiter.")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=10000,
        help="Rows per batch (larger is faster, more memory).",
    )

    parser.add_argument("--int-min", type=int, default=0, help="Minimum int value.")
    parser.add_argument("--int-max", type=int, default=1_000_000, help="Maximum int value.")
    parser.add_argument("--float-min", type=float, default=0.0, help="Minimum float value.")
    parser.add_argument("--float-max", type=float, default=1_000_000.0, help="Maximum float value.")
    parser.add_argument(
        "--float-precision", type=int, default=6, help="Float precision."
    )
    parser.add_argument("--str-min-len", type=int, default=5, help="Min string length.")
    parser.add_argument("--str-max-len", type=int, default=20, help="Max string length.")

    args, unknown = parser.parse_known_args(argv)
    args._unknown = unknown
    return args


def validate_types(cols: List[str], types: List[str]) -> List[str]:
    if len(types) == 1 and len(cols) > 1:
        types = types * len(cols)
    if len(types) != len(cols):
        raise SystemExit(
            "data_types must be length 1 or match number of columns."
        )
    normalized = []
    for col_type in types:
        col_type = col_type.strip().lower()
        if col_type not in {"int", "float", "str"}:
            raise SystemExit(f"Unsupported data type: {col_type}")
        normalized.append(col_type)
    return normalized


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    cols = parse_list(args.cols)
    if not cols:
        raise SystemExit("No columns provided.")

    types = validate_types(cols, parse_list(args.data_types))
    lovs, remaining = parse_lov_args(args._unknown)
    unknown_flags = remaining
    if unknown_flags:
        raise SystemExit(f"Unknown arguments: {' '.join(unknown_flags)}")

    for col in lovs:
        if col not in cols:
            raise SystemExit(f"--lov_{col} provided but {col} is not in cols.")

    if args.seed is not None:
        random.seed(args.seed)
        if np is not None:
            np.random.seed(args.seed)

    generators = build_generators(
        cols,
        types,
        lovs,
        args.int_min,
        args.int_max,
        args.float_min,
        args.float_max,
        args.float_precision,
        args.str_min_len,
        args.str_max_len,
    )

    output_path = args.output
    if output_path is None:
        output_path = "testdata.parquet" if args.format == "parquet" else "testdata.csv"

    if args.format == "parquet":
        if output_path == "-":
            raise SystemExit("Parquet output does not support stdout.")
        if np is None:
            raise SystemExit("Parquet output requires numpy (and pyarrow installed).")
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise SystemExit("Parquet output requires pyarrow.") from exc

        remaining = args.rows
        if remaining <= 0:
            return 0

        total_start = time.perf_counter()
        batch = min(args.chunk_size, remaining)
        start = time.perf_counter()
        columns = [gen(batch) for gen in generators]
        table = pa.Table.from_pydict(dict(zip(cols, columns)))
        writer = pq.ParquetWriter(output_path, table.schema, compression=args.compression)
        writer.write_table(table)
        elapsed = max(time.perf_counter() - start, 1e-6)
        est_total = elapsed * (args.rows / batch)
        print(
            f"ETA (rough): {format_duration(est_total)} for {args.rows} rows.",
            file=sys.stderr,
        )
        remaining -= batch

        while remaining > 0:
            batch = min(args.chunk_size, remaining)
            columns = [gen(batch) for gen in generators]
            table = pa.Table.from_pydict(dict(zip(cols, columns)))
            writer.write_table(table)
            remaining -= batch

        writer.close()
        total_elapsed = time.perf_counter() - total_start
        print(
            f"Total time: {format_duration(total_elapsed)} for {args.rows} rows.",
            file=sys.stderr,
        )
        return 0

    if output_path == "-":
        out_fh = sys.stdout
    else:
        out_fh = open(output_path, "w", newline="", encoding="utf-8")

    with out_fh:
        writer = csv.writer(out_fh, delimiter=args.delimiter)
        writer.writerow(cols)
        if args.rows <= 0:
            return 0
        total_start = time.perf_counter()
        batch = min(args.chunk_size, args.rows)
        start = time.perf_counter()
        columns = [gen(batch) for gen in generators]
        for row in zip(*columns):
            writer.writerow(row)
        elapsed = max(time.perf_counter() - start, 1e-6)
        est_total = elapsed * (args.rows / batch)
        print(
            f"ETA (rough): {format_duration(est_total)} for {args.rows} rows.",
            file=sys.stderr,
        )
        remaining = args.rows - batch
        while remaining > 0:
            batch = min(args.chunk_size, remaining)
            columns = [gen(batch) for gen in generators]
            for row in zip(*columns):
                writer.writerow(row)
            remaining -= batch
        total_elapsed = time.perf_counter() - total_start
        print(
            f"Total time: {format_duration(total_elapsed)} for {args.rows} rows.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
