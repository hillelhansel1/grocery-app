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
    item_status: str
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
