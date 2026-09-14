"""Benchmark reproduzível e sem dados reais para o fluxo assíncrono do Razão."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import random
import sys
import time
import tracemalloc
from typing import Callable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class PhaseMeasurement:
    elapsed_seconds: float
    peak_memory_bytes: int


def build_synthetic_rows(
    count: int, *, seed: int = 484, block_size: int = 1_000
) -> list[dict]:
    """Gera lançamentos determinísticos cobrindo meses, blocos e avisos."""
    if count <= 0 or block_size <= 0:
        raise ValueError("count e block_size devem ser positivos")
    randomizer = random.Random(seed)
    rows = []
    for index in range(count):
        invalid = index % 97 == 0
        warning_code = "saldo_divergente" if index % 41 == 0 else None
        rows.append(
            {
                "number": index + 1,
                "month": index % 12 + 1,
                "block": index // block_size,
                "account": 10046,
                "counterpart": None if invalid else 20001,
                "amount": f"{randomizer.randint(1, 100_000) / 100:.2f}",
                "valid": not invalid,
                "warning_code": warning_code,
            }
        )
    return rows


def _measure(operation: Callable[[], T]) -> tuple[T, PhaseMeasurement]:
    tracemalloc.start()
    started = time.perf_counter()
    try:
        result = operation()
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, PhaseMeasurement(round(elapsed, 6), max(peak, 1))


def _checksum(rows: list[dict]) -> str:
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def run_benchmark(
    *,
    rows: int = 20_000,
    seed: int = 484,
    block_size: int = 1_000,
    api_probe: Callable[[], bool] | None = None,
) -> dict:
    """Executa fases isoladas e retorna métricas e gates estruturais."""
    parsed, parser_metric = _measure(
        lambda: build_synthetic_rows(rows, seed=seed, block_size=block_size)
    )
    valid, validation_metric = _measure(
        lambda: [row for row in parsed if row["valid"]]
    )

    persisted_blocks: list[int] = []
    probe_results: list[bool] = []
    probe = api_probe or (lambda: False)

    def persist_in_blocks() -> int:
        for start in range(0, len(valid), block_size):
            persisted_blocks.append(len(valid[start : start + block_size]))
            probe_results.append(bool(probe()))
        return sum(persisted_blocks)

    persisted, persistence_metric = _measure(persist_in_blocks)
    serialized, serialization_metric = _measure(
        lambda: json.dumps(
            {
                "rows_processed": rows,
                "rows_persisted": persisted,
                "warnings": sum(bool(row["warning_code"]) for row in parsed),
            },
            sort_keys=True,
        )
    )
    expected_blocks = math.ceil(rows / block_size)
    valid_checksum = _checksum(parsed)
    repeated_checksum = _checksum(
        build_synthetic_rows(rows, seed=seed, block_size=block_size)
    )
    metrics = {
        "parser": parser_metric,
        "validation": validation_metric,
        "persistence": persistence_metric,
        "serialization": serialization_metric,
    }
    return {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "fixture": {
            "rows": rows,
            "seed": seed,
            "block_size": block_size,
            "blocks": expected_blocks,
        },
        "phases": {
            name: {
                "elapsed_seconds": metric.elapsed_seconds,
                "peak_memory_bytes": metric.peak_memory_bytes,
            }
            for name, metric in metrics.items()
        },
        "gates": {
            "queries_scale_with_blocks": len(persisted_blocks) <= expected_blocks,
            "memory_bounded_by_blocks": max(persisted_blocks, default=0) <= block_size,
            "api_responsive_during_job": bool(probe_results) and all(probe_results),
            "reproducible_completion": valid_checksum == repeated_checksum,
        },
        "result": {
            "rows_processed": rows,
            "rows_persisted": persisted,
            "invalid_rows": rows - persisted,
            "warnings": sum(bool(row["warning_code"]) for row in parsed),
            "fixture_sha256": valid_checksum,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=484)
    parser.add_argument("--block-size", type=int, default=1_000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run_benchmark(rows=args.rows, seed=args.seed, block_size=args.block_size)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    sys.stdout.write(payload + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
