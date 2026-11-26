import re
from datetime import datetime
from typing import NamedTuple
from xml.etree import ElementTree as ET

from .models import FeedKind, PriceObservation, Retailer, SourceProduct, Store
from .xmlfeed import digits, elements, field, identifier, number, scalar

HEADER = ("ChainID", "SubChainID", "StoreID")
ITEMS = ("Root", "Items")


class PriceBatch(NamedTuple):
    store: Store
    observations: tuple[PriceObservation, ...]
    rejected: tuple[str, ...]


def read_prices(
    payload: bytes, source: str, kind: FeedKind, *, fractional_time: bool
) -> PriceBatch:
    headers: dict[str, str] = {}
    store = None
    observations: dict[tuple[str, str], PriceObservation] = {}
    rejected = []
    seen: set[tuple[str, str]] = set()
    containers = 0
    rows = 0
    selected = {("Root", tag) for tag in HEADER} | {ITEMS + ("*",)}
    # The iterator selects element paths by tag. Any unexpected child of Items
    # is surfaced through the wildcard and rejected as a row.
    for path, node in elements(payload, selected, watch={ITEMS}):
        if path[:1] != ("Root",):
            raise ValueError(f"expected {source} Root/Items")
        if len(path) == 2 and path[-1] in HEADER:
            tag = path[-1]
            if tag in headers:
                raise ValueError(f"{tag}: duplicate header")
            headers[tag] = digits(scalar(node), tag)
        elif path == ITEMS:
            containers += 1
        elif path[:2] == ITEMS and len(path) == 3:
            if store is None:
                store = store_from_header(source, headers)
            rows += 1
            try:
                if node.tag != "Item":
                    raise ValueError("expected Item")
                key = identifier(node, "ItemType"), identifier(node, "ItemCode")
                if key in seen:
                    rejected.append(f"row {rows}: duplicate source product")
                    first = observations.pop(key, None)
                    if first is not None:
                        rejected.append(
                            f"row {first.source_row}: duplicate source product"
                        )
                    continue
                seen.add(key)
                observations[key] = read_row(
                    node, store, rows, key, kind, fractional_time
                )
            except ValueError as exc:
                rejected.append(f"row {rows}: {exc}")
    if containers != 1:
        raise ValueError(f"expected {source} Root/Items")
    return PriceBatch(
        store or store_from_header(source, headers),
        tuple(observations.values()),
        tuple(rejected),
    )


def store_from_header(source: str, headers: dict[str, str]) -> Store:
    try:
        return Store(
            Retailer(source, headers["ChainID"]),
            headers["SubChainID"],
            headers["StoreID"],
        )
    except KeyError as exc:
        raise ValueError(f"{exc.args[0]}: missing header before Items") from exc


def read_row(
    item: ET.Element,
    store: Store,
    row: int,
    key: tuple[str, str],
    kind: FeedKind,
    fractional_time: bool,
) -> PriceObservation:
    updated_at = field(item, "PriceUpdateTime")
    pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    if fractional_time:
        pattern += r"(?:\.[0-9]{1,6})?"
    if not re.fullmatch(pattern, updated_at):
        raise ValueError("PriceUpdateTime: expected local ISO timestamp")
    status = field(item, "ItemStatus", optional=kind == FeedKind.SNAPSHOT)
    return PriceObservation(
        store,
        SourceProduct(
            store.retailer,
            *key,
            field(item, "ItemName"),
            number(item, "Quantity", positive=True),
            field(item, "UnitQty"),
        ),
        number(item, "ItemPrice"),
        datetime.fromisoformat(updated_at),
        row,
        digits(status, "ItemStatus") if status else None,
    )
