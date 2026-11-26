from datetime import datetime
from hashlib import sha256
from urllib.parse import urlsplit

from . import shufersal
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
) -> IngestionRun:
    if attempted_at.utcoffset() is None:
        raise ValueError("attempted_at requires a timezone")
    if acquisition_failed and payload is not None:
        raise ValueError("acquisition failure cannot include a payload")
    url = urlsplit(source_url)
    safe_url = url._replace(
        netloc=url.netloc.rsplit("@", 1)[-1], query="", fragment=""
    ).geturl()
    if payload is None:
        status = RunStatus.FAILED if acquisition_failed else RunStatus.MISSING
        error = "acquisition failed" if acquisition_failed else None
        return IngestionRun(
            run_id,
            safe_url,
            attempted_at,
            kind,
            status,
            store=expected_store,
            error=error,
        )

    digest = sha256(payload).hexdigest()
    try:
        store, observations = shufersal.parse(payload)
        if expected_store is not None and store != expected_store:
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
    return IngestionRun(
        run_id,
        safe_url,
        attempted_at,
        kind,
        RunStatus.SUCCESS,
        digest,
        store,
        observations,
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
        PriceState.MISSING if run.kind == FeedKind.SNAPSHOT else PriceState.NOT_OBSERVED
    )
