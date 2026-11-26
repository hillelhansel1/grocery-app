"""Measure a local PriceFull payload and verify its directory mapping."""

import argparse
import tracemalloc
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from ingestion import carrefour, shufersal
from ingestion.models import FeedKind
from ingestion.run import ingest_prices


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=("shufersal", "carrefour"))
    parser.add_argument("price", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--price-url")
    parser.add_argument("--directory-url")
    args = parser.parse_args()

    payload = args.price.read_bytes()
    options = {
        "run_id": "benchmark",
        "source_url": args.price_url or args.price.resolve().as_uri(),
        "attempted_at": datetime.now(UTC),
        "kind": FeedKind.SNAPSHOT,
        "expected_bytes": len(payload),
    }
    adapter = shufersal if args.source == "shufersal" else carrefour
    start = perf_counter()
    batch = adapter.inspect_prices(payload, FeedKind.SNAPSHOT)
    elapsed = perf_counter() - start
    valid = len(batch.observations)
    unique = len({row.product.key for row in batch.observations})
    rejected = len(batch.rejected)

    tracemalloc.start()
    memory_batch = adapter.inspect_prices(payload, FeedKind.SNAPSHOT)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if batch != memory_batch:
        raise RuntimeError("benchmark runs produced different results")
    run = ingest_prices(payload, source=args.source, **options)
    print(
        f"{args.source}: {run.status}, {len(payload)} bytes, SHA-256 {run.payload_sha256}"
    )
    print(
        f"{valid + rejected} rows, {valid} valid, {rejected} rejected, {unique} unique accepted"
    )
    print(f"{elapsed:.3f} s, {peak / 2**20:.2f} MiB traced Python peak")
    if batch.rejected:
        print(Counter(message.split(": ", 1)[-1] for message in batch.rejected))
    directory = adapter.parse_directory(
        args.directory.read_bytes(),
        args.directory_url or args.directory.resolve().as_uri(),
    )
    print(f"{len(directory.locations)} stores, SHA-256 {directory.payload_sha256}")
    print(f"Snapshot store {batch.store.subchain_id}/{batch.store.store_id}")
    location = directory.location_for(batch.store)
    if location is None:
        raise SystemExit(run.error or "Snapshot store is missing from the directory")
    print(f"Directory match {location.store.subchain_id}/{location.store.store_id}")
    if run.store is None:
        raise SystemExit(run.error)


if __name__ == "__main__":
    main()
