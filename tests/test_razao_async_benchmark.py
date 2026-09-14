import json
import subprocess
import sys

from benchmarks.razao_async import build_synthetic_rows, run_benchmark


def test_synthetic_rows_are_deterministic_and_representative():
    first = build_synthetic_rows(2_500, seed=484, block_size=1_000)
    second = build_synthetic_rows(2_500, seed=484, block_size=1_000)

    assert first == second
    assert len(first) == 2_500
    assert len({row["month"] for row in first}) == 12
    assert {row["block"] for row in first} == {0, 1, 2}
    assert any(not row["valid"] for row in first)
    assert any(row["warning_code"] for row in first)


def test_benchmark_reports_each_phase_and_structural_gates():
    probes = []
    report = run_benchmark(
        rows=2_500,
        seed=484,
        block_size=1_000,
        api_probe=lambda: probes.append("ok") or True,
    )

    assert report["fixture"] == {
        "rows": 2_500,
        "seed": 484,
        "block_size": 1_000,
        "blocks": 3,
    }
    assert set(report["phases"]) == {
        "parser",
        "validation",
        "persistence",
        "serialization",
    }
    assert all(phase["elapsed_seconds"] >= 0 for phase in report["phases"].values())
    assert all(phase["peak_memory_bytes"] > 0 for phase in report["phases"].values())
    assert report["gates"] == {
        "queries_scale_with_blocks": True,
        "memory_bounded_by_blocks": True,
        "api_responsive_during_job": True,
        "reproducible_completion": True,
    }
    assert report["result"]["rows_processed"] == 2_500
    assert report["result"]["invalid_rows"] > 0
    assert report["result"]["warnings"] > 0
    assert len(probes) == 3


def test_responsiveness_gate_fails_when_any_probe_fails():
    answers = iter([True, False, True])

    report = run_benchmark(
        rows=120,
        seed=484,
        block_size=50,
        api_probe=lambda: next(answers),
    )

    assert report["gates"]["api_responsive_during_job"] is False


def test_benchmark_cli_writes_reproducible_json(tmp_path):
    output = tmp_path / "razao-benchmark.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "benchmarks.razao_async",
            "--rows",
            "120",
            "--seed",
            "484",
            "--block-size",
            "50",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert json.loads(completed.stdout) == report
    assert report["environment"]["python"]
    assert report["fixture"]["blocks"] == 3
    assert report["gates"]["api_responsive_during_job"] is False
