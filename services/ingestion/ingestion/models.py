from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal


class FeedKind(StrEnum):
    SNAPSHOT = "snapshot"
    DELTA = "delta"


class RunStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    MISSING = "missing"
    FAILED = "failed"


class PriceState(StrEnum):
    NEW = "new"
    CHANGED = "changed"
    UNCHANGED = "unchanged"
    MISSING = "missing"
    NOT_OBSERVED = "not_observed"
    FAILED = "failed"


@dataclass(frozen=True)
class Retailer:
    source: str
    chain_id: str


@dataclass(frozen=True)
class Store:
    retailer: Retailer
    subchain_id: str
    store_id: str

    @property
    def directory_key(self) -> tuple[Retailer, str, str]:
        if self.retailer.source == "shufersal":
            return (
                self.retailer,
                self.subchain_id.lstrip("0") or "0",
                self.store_id.lstrip("0") or "0",
            )
        return self.retailer, self.subchain_id, self.store_id


@dataclass(frozen=True)
class SourceProduct:
    retailer: Retailer
    item_type: str
    item_code: str
    name: str
    quantity: Decimal
    quantity_unit: str

    @property
    def key(self) -> tuple[str, str]:
        return self.item_type, self.item_code


@dataclass(frozen=True)
class PriceObservation:
    store: Store
    product: SourceProduct
    amount: Decimal
    source_updated_at: datetime
    source_row: int
    item_status: str | None
    currency: Literal["ILS"] = "ILS"


@dataclass(frozen=True)
class IngestionRun:
    run_id: str
    source_url: str
    attempted_at: datetime
    kind: FeedKind
    status: RunStatus
    payload_sha256: str | None = None
    store: Store | None = None
    observations: tuple[PriceObservation, ...] = ()
    error: str | None = None

    rejected: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoreLocation:
    store: Store
    name: str
    address: str | None
    city: str | None
    postal_code: str | None


@dataclass(frozen=True)
class StoreDirectory:
    retailer: Retailer
    retailer_name: str
    locations: tuple[StoreLocation, ...]
    source_url: str
    payload_sha256: str

    def location_for(self, store: Store) -> StoreLocation | None:
        return next(
            (
                location
                for location in self.locations
                if location.store.directory_key == store.directory_key
            ),
            None,
        )
