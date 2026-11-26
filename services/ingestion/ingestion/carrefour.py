from .directory import read_directory
from .models import FeedKind, StoreDirectory
from .prices import PriceBatch, read_prices


def inspect_prices(payload: bytes, kind: FeedKind) -> PriceBatch:
    return read_prices(payload, "carrefour", kind, fractional_time=True)


def parse_directory(payload: bytes, source_url: str) -> StoreDirectory:
    return read_directory(payload, source_url, "carrefour", "Root", allow_utf16=True)
