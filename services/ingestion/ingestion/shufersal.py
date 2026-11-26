from .directory import read_directory
from .models import FeedKind, PriceObservation, Store, StoreDirectory
from .prices import PriceBatch, read_prices


def inspect_prices(payload: bytes, kind: FeedKind) -> PriceBatch:
    return read_prices(payload, "shufersal", kind, fractional_time=False)


def parse(payload: bytes) -> tuple[Store, tuple[PriceObservation, ...]]:
    batch = inspect_prices(payload, FeedKind.DELTA)
    if batch.rejected:
        raise ValueError(batch.rejected[0])
    return batch.store, batch.observations


def parse_directory(payload: bytes, source_url: str) -> StoreDirectory:
    return read_directory(payload, source_url, "shufersal", "Chain")
