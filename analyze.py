#!/usr/bin/env python3
"""Offline, read-only AFR log analyzer.

This tool never connects to a motorcycle or writes a flashable tune. It reads a
wideband logger CSV and produces *review-only* fuel-trim estimates.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


REQUIRED = {"rpm", "tps", "afr"}


def load_rows(path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV must have a header row: rpm,tps,afr")
        names = {name.strip().lower() for name in reader.fieldnames if name}
        missing = REQUIRED - names
        if missing:
            raise ValueError("Missing required CSV columns: " + ", ".join(sorted(missing)))
        # Normalize headers, allowing common extra columns such as gear or time.
        for line_no, raw in enumerate(reader, start=2):
            row = {str(k).strip().lower(): v for k, v in raw.items() if k is not None}
            try:
                rpm, tps, afr = (float(row[k]) for k in ("rpm", "tps", "afr"))
            except (TypeError, ValueError):
                continue  # Ignore blank/non-numeric logger rows.
            if not all(math.isfinite(x) for x in (rpm, tps, afr)):
                continue
            if rpm <= 0 or not 0 <= tps <= 100 or not 5 <= afr <= 25:
                continue
            rows.append({"rpm": rpm, "tps": tps, "afr": afr, "line": float(line_no)})
    if not rows:
        raise ValueError("No usable rows. Check headers and numeric values.")
    return rows


def analyze(rows: list[dict[str, float]], target_afr: float, rpm_bin: int,
            tps_bin: int, min_samples: int) -> list[dict[str, float | int | str]]:
    if not 5 <= target_afr <= 25:
        raise ValueError("Target AFR must be between 5 and 25")
    if rpm_bin <= 0 or tps_bin <= 0 or min_samples <= 0:
        raise ValueError("Bin sizes and minimum samples must be positive")

    cells: dict[tuple[int, int], list[float]] = defaultdict(list)
    for row in rows:
        rbin = int(row["rpm"] // rpm_bin * rpm_bin)
        tbin = int(row["tps"] // tps_bin * tps_bin)
        cells[(rbin, tbin)].append(row["afr"])

    output = []
    for (rbin, tbin), afrs in sorted(cells.items()):
        observed = statistics.median(afrs)
        enough = len(afrs) >= min_samples
        # Approximate fuel trim: measured AFR / target AFR - 1.
        # This is advisory only; real calibration requires controlled load,
        # sensor validation, and an appropriate target table.
        trim = (observed / target_afr - 1.0) * 100.0 if enough else ""
        output.append({
            "rpm_bin_start": rbin,
            "tps_bin_start_percent": tbin,
            "samples": len(afrs),
            "median_afr": round(observed, 3),
            "requested_target_afr": target_afr,
            "estimated_fuel_trim_percent": round(trim, 2) if enough else "",
            "status": "review" if enough else "insufficient samples",
        })
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="wideband CSV with rpm,tps,afr columns")
    parser.add_argument("-o", "--output", type=Path, default=Path("suggestions.csv"))
    parser.add_argument("--target-afr", type=float, default=13.2,
                        help="single illustrative target; set deliberately for your use case")
    parser.add_argument("--rpm-bin", type=int, default=500)
    parser.add_argument("--tps-bin", type=int, default=10)
    parser.add_argument("--min-samples", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        if args.input.resolve() == args.output.resolve() or (
            args.output.exists() and args.input.samefile(args.output)
        ):
            raise ValueError("Output must be a different file from the input log")
        rows = load_rows(args.input)
        results = analyze(rows, args.target_afr, args.rpm_bin, args.tps_bin, args.min_samples)
        with args.output.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0]))
            writer.writeheader()
            writer.writerows(results)
        print(f"Read {len(rows)} valid samples; wrote {len(results)} cells to {args.output}")
        print("Review-only estimates; this program does not connect to or tune the bike.")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
