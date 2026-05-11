from __future__ import annotations

import json
import math
import os
import socket
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "measurements"


CONSISTENCY_LEVELS = [
    ("ONE", ConsistencyLevel.ONE),
    ("LOCAL_QUORUM", ConsistencyLevel.LOCAL_QUORUM),
    ("ALL", ConsistencyLevel.ALL),
]

INSERT_CQL = """
INSERT INTO sensor_readings (
    sensor_id, reading_time, metric_type, value, unit, quality_flag
)
VALUES (?, ?, ?, ?, ?, ?)
"""


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"').strip("'")
    return {**values, **os.environ}


def reachable_host(host: str) -> str:
    try:
        socket.gethostbyname(host)
        return host
    except socket.gaierror:
        return "localhost"


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = math.ceil((pct / 100) * len(ordered)) - 1
    return ordered[max(0, min(index, len(ordered) - 1))]


def make_params(level_name: str, run_id: str, index: int) -> tuple[Any, ...]:
    sensor_id = f"BENCH_{level_name}_{run_id}_{index % 20:03d}"
    reading_time = datetime(2026, 5, 11, tzinfo=timezone.utc) + timedelta(
        milliseconds=index
    )
    metric_type = "voltage"
    value = 225.0 + ((index % 100) / 10)
    return sensor_id, reading_time, metric_type, value, "V", 0


def write_one(session, prepared, consistency_level: int, params: tuple[Any, ...]) -> float:
    statement = prepared.bind(params)
    statement.consistency_level = consistency_level
    started = time.perf_counter()
    session.execute(statement)
    return (time.perf_counter() - started) * 1000


def run_consistency_level(
    session,
    level_name: str,
    consistency_level: int,
    event_count: int,
    concurrency: int,
    run_id: str,
) -> dict[str, Any]:
    prepared = session.prepare(INSERT_CQL)
    latencies_ms: list[float] = []
    errors: list[str] = []
    submitted = 0

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = set()

        while submitted < event_count and len(futures) < concurrency:
            params = make_params(level_name, run_id, submitted)
            futures.add(
                executor.submit(write_one, session, prepared, consistency_level, params)
            )
            submitted += 1

        while futures:
            done, futures = wait(futures, return_when=FIRST_COMPLETED)
            for future in done:
                try:
                    latencies_ms.append(future.result())
                except Exception as exc:  # Keep benchmark honest; report all failures.
                    errors.append(f"{type(exc).__name__}: {exc}")

                if submitted < event_count:
                    params = make_params(level_name, run_id, submitted)
                    futures.add(
                        executor.submit(
                            write_one,
                            session,
                            prepared,
                            consistency_level,
                            params,
                        )
                    )
                    submitted += 1

    duration_seconds = time.perf_counter() - started
    successful = len(latencies_ms)
    return {
        "consistency_level": level_name,
        "attempted_events": event_count,
        "successful_events": successful,
        "errors": len(errors),
        "sample_errors": errors[:5],
        "duration_seconds": round(duration_seconds, 3),
        "events_per_second": round(successful / duration_seconds, 2)
        if duration_seconds
        else 0,
        "p50_latency_ms": round(percentile(latencies_ms, 50), 3)
        if latencies_ms
        else None,
        "p95_latency_ms": round(percentile(latencies_ms, 95), 3)
        if latencies_ms
        else None,
    }


def print_results(results: list[dict[str, Any]]) -> None:
    print()
    print("| Consistency | Events/s | p50 ms | p95 ms | Errors |")
    print("|---|---:|---:|---:|---:|")
    for result in results:
        print(
            "| {consistency_level} | {events_per_second} | {p50_latency_ms} | "
            "{p95_latency_ms} | {errors} |".format(**result)
        )
    print()


def main() -> None:
    env = load_env()
    host = reachable_host(env.get("CASSANDRA_HOST", "timeseries-db"))
    port = int(env.get("CASSANDRA_PORT", "9042"))
    keyspace = env.get("CASSANDRA_KEYSPACE", "gridsense")
    event_count = int(env.get("CASSANDRA_MEASURE_EVENTS", "10000"))
    concurrency = int(env.get("CASSANDRA_MEASURE_CONCURRENCY", "64"))
    run_id = env.get("CASSANDRA_MEASURE_RUN_ID", uuid4().hex[:8])

    cluster = Cluster([host], port=port)
    session = cluster.connect(keyspace)

    results: list[dict[str, Any]] = []
    try:
        for level_name, consistency_level in CONSISTENCY_LEVELS:
            print(
                f"Measuring {level_name}: events={event_count}, "
                f"concurrency={concurrency}, run_id={run_id}"
            )
            results.append(
                run_consistency_level(
                    session=session,
                    level_name=level_name,
                    consistency_level=consistency_level,
                    event_count=event_count,
                    concurrency=concurrency,
                    run_id=run_id,
                )
            )
    finally:
        cluster.shutdown()

    print_results(results)
    RESULTS_DIR.mkdir(exist_ok=True)
    output_path = RESULTS_DIR / f"cassandra_consistency_{run_id}.json"
    output_path.write_text(json.dumps(results, indent=2))
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
