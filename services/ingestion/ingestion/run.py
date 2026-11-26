import re
from datetime import datetime
from hashlib import sha256
from typing import Literal

from . import carrefour, shufersal
from .directory import public_url
from .models import (
    FeedKind,
    IngestionRun,
    PriceObservation,
    PriceState,
    RunStatus,
    Store,
)


def ingest_shufersal(
    payload: bytes | None,
    *,
    run_id: str,
    source_url: str,
    attempted_at: datetime,
    kind: FeedKind,
    expected_store: Store | None = None,
    acquisition_failed: bool = False,
    expected_bytes: int | None = None,
) -> IngestionRun:
    return ingest_prices(
        payload,
        source="shufersal",
        run_id=run_id,
        source_url=source_url,
        attempted_at=attempted_at,
        kind=kind,
        expected_store=expected_store,
        acquisition_failed=acquisition_failed,
        expected_bytes=expected_bytes,
    )


def ingest_prices(
    payload: bytes | None,
    *,
    source: Literal["shufersal", "carrefour"],
    run_id: str,
    source_url: str,
    attempted_at: datetime,
    kind: FeedKind,
    expected_store: Store | None = None,
    acquisition_failed: bool = False,
    expected_bytes: int | None = None,
) -> IngestionRun:
    if attempted_at.utcoffset() is None:
        raise ValueError("attempted_at requires a timezone")
    safe_url = public_url(source_url)
    digest = sha256(payload).hexdigest() if payload is not None else None
    if acquisition_failed or (
        expected_bytes is not None
        and (payload is None or len(payload) != expected_bytes)
    ):
        return IngestionRun(
            run_id,
            safe_url,
            attempted_at,
            kind,
            RunStatus.FAILED,
            digest,
            expected_store,
            error="acquisition failed or payload length differs from expected",
        )
    if payload is None:
        return IngestionRun(
            run_id,
            safe_url,
            attempted_at,
            kind,
            RunStatus.MISSING,
            store=expected_store,
        )

    try:
        filename = safe_url.rsplit("/", 1)[-1]
        match = re.match(r"(PriceFull|Price)[0-9]", filename, re.IGNORECASE)
        if match and (match[1].lower() == "pricefull") != (kind == FeedKind.SNAPSHOT):
            raise ValueError("feed kind does not match filename")
        adapter = shufersal if source == "shufersal" else carrefour
        batch = adapter.inspect_prices(payload, kind)
        named_ids = re.match(
            r"Price(?:Full)?([0-9]+)-([0-9]+)-([0-9]+)-", filename, re.IGNORECASE
        )
        if named_ids and named_ids.groups() != (
            batch.store.retailer.chain_id,
            batch.store.subchain_id,
            batch.store.store_id,
        ):
            raise ValueError("price header identifiers do not match filename")
        if expected_store is not None and batch.store != expected_store:
            raise ValueError("store does not match expected store")
    except ValueError as exc:
        return IngestionRun(
            run_id,
            safe_url,
            attempted_at,
            kind,
            RunStatus.FAILED,
            digest,
            expected_store,
            error=str(exc),
        )
    if not batch.rejected:
        status = RunStatus.SUCCESS
    elif kind == FeedKind.SNAPSHOT and batch.observations:
        status = RunStatus.PARTIAL
    else:
        status = RunStatus.FAILED
    return IngestionRun(
        run_id,
        safe_url,
        attempted_at,
        kind,
        status,
        digest,
        batch.store,
        batch.observations if status != RunStatus.FAILED else (),
        error=batch.rejected[0] if batch.rejected else None,
        rejected=batch.rejected,
    )


def price_state(
    run: IngestionRun,
    store: Store,
    key: tuple[str, str],
    previous: PriceObservation | None = None,
) -> PriceState:
    if run.store != store:
        raise ValueError("run must be scoped to the requested store")
    if previous is not None and (
        previous.store != store or previous.product.key != key
    ):
        raise ValueError("previous observation must match store and product")
    if run.status == RunStatus.FAILED:
        return PriceState.FAILED
    if run.status == RunStatus.MISSING:
        return PriceState.MISSING
    for observation in run.observations:
        if observation.product.key == key:
            if previous is None:
                return PriceState.NEW
            if observation.amount == previous.amount:
                return PriceState.UNCHANGED
            return PriceState.CHANGED
    return (
        PriceState.MISSING
        if run.kind == FeedKind.SNAPSHOT and run.status == RunStatus.SUCCESS
        else PriceState.NOT_OBSERVED
    )
