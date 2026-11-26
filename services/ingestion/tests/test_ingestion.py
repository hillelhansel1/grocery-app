from datetime import UTC, datetime
from decimal import Decimal
from gzip import compress
from hashlib import sha256

import pytest

from ingestion.models import FeedKind, PriceState, Retailer, RunStatus, Store
from ingestion.run import ingest_shufersal, price_state

# Synthetic data using the verified Shufersal layout.
ITEM = """<Item>
  <ItemType>0</ItemType><ItemCode>00042</ItemCode><ItemName>לחם</ItemName>
  <Quantity>0.5</Quantity><UnitQty>kg</UnitQty><ItemPrice>9.90</ItemPrice>
  <PriceUpdateTime>2026-11-26T12:34:56</PriceUpdateTime><ItemStatus>1</ItemStatus>
</Item>"""
DOCUMENT = """<Root><ChainID>7290027600007</ChainID><SubChainID>001</SubChainID>
<StoreID>007</StoreID><Items>{items}</Items></Root>"""
STORE = Store(Retailer("shufersal", "7290027600007"), "001", "007")
KEY = ("0", "00042")
URL = "https://example.invalid/Price.gz"


def payload(items: str = ITEM) -> bytes:
    return DOCUMENT.format(items=items).encode("utf-8")


def run(data: bytes | None, kind: FeedKind = FeedKind.DELTA, *, failed: bool = False):
    return ingest_shufersal(
        data,
        run_id="test",
        source_url=URL + "?sig=sample#fragment",
        attempted_at=datetime(2026, 11, 27, tzinfo=UTC),
        kind=kind,
        expected_store=STORE,
        acquisition_failed=failed,
    )


def test_normalizes_bom_gzip_and_retains_provenance():
    data = compress(b"\xef\xbb\xbf" + payload(), mtime=0)
    result = run(data)
    assert result.status == RunStatus.SUCCESS
    assert result.run_id == "test"
    assert result.source_url == URL
    assert result.payload_sha256 == sha256(data).hexdigest()
    assert result.store == STORE
    (observation,) = result.observations
    assert observation.store == STORE
    assert observation.product.key == KEY
    assert observation.product.name == "לחם"
    assert observation.product.quantity == Decimal("0.5")
    assert observation.product.quantity_unit == "kg"
    assert observation.amount == Decimal("9.90")
    assert observation.currency == "ILS"
    assert observation.source_updated_at == datetime(2026, 11, 26, 12, 34, 56)
    assert observation.source_row == 1


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [
        ("9.90", "-1", "ItemPrice"),
        ("9.90", "NaN", "ItemPrice"),
        ("9.90", "9.999", "ItemPrice"),
        ("9.90", "1e4", "ItemPrice"),
        ("0.5", "0", "Quantity"),
        ("0.5", "-0.1", "Quantity"),
        ("00042", "00A42", "ItemCode"),
        ("00042", "１２", "ItemCode"),
        ("<ItemName>לחם</ItemName>", "", "ItemName"),
        ("לחם", " ", "ItemName"),
        ("לחם", "\ufffd", "ItemName"),
        ("לחם", "<b>name</b>", "ItemName"),
        (
            "<ItemName>לחם</ItemName>",
            "<ItemName>a</ItemName><ItemName>b</ItemName>",
            "ItemName",
        ),
        ("2026-11-26T12:34:56", "2026-11-31T12:34:56", "row 1"),
    ],
)
def test_invalid_row(old, new, error):
    result = run(payload(ITEM.replace(old, new)))
    assert result.status == RunStatus.FAILED
    assert result.error and error in result.error
    assert result.observations == ()


@pytest.mark.parametrize(
    ("data", "error"),
    [
        (b"\xff<Root/>", "UTF-8"),
        (
            b"<?xml version='1.0' encoding='windows-1255'?><Root/>",
            "encoding declaration",
        ),
        (b"<Root>", "malformed XML"),
        (b"<!DOCTYPE Root><Root/>", "DTD"),
        (b"\x1f\x8b", "gzip"),
        (b"<Prices/>", "Root/Items"),
        (payload().replace(b"<StoreID>007", b"<StoreID>008"), "expected store"),
        (payload(ITEM * 2), "row 2: duplicate source product"),
        (payload().replace(b"<ChainID>7290027600007", b"<ChainID>abc"), "ChainID"),
    ],
)
def test_invalid_document_is_atomic(data, error):
    result = run(data)
    assert result.status == RunStatus.FAILED
    assert result.error and error in result.error
    assert result.observations == ()
    assert result.payload_sha256 == sha256(data).hexdigest()


def test_price_states_require_comparable_observations():
    baseline = run(payload())
    (previous,) = baseline.observations
    assert price_state(baseline, STORE, KEY) == PriceState.NEW
    equal = run(payload(ITEM.replace("9.90", "9.900")))
    assert price_state(equal, STORE, KEY, previous) == PriceState.UNCHANGED
    changed = run(payload(ITEM.replace("9.90", "10")))
    assert price_state(changed, STORE, KEY, previous) == PriceState.CHANGED
    assert (
        price_state(run(payload("")), STORE, KEY, previous) == PriceState.NOT_OBSERVED
    )
    assert (
        price_state(run(payload(""), FeedKind.SNAPSHOT), STORE, KEY, previous)
        == PriceState.MISSING
    )
    assert price_state(run(None), STORE, KEY, previous) == PriceState.MISSING
    assert (
        price_state(run(None, failed=True), STORE, KEY, previous) == PriceState.FAILED
    )
    assert price_state(run(b"garbage"), STORE, KEY, previous) == PriceState.FAILED
    with pytest.raises(ValueError, match="store"):
        price_state(baseline, Store(STORE.retailer, "001", "008"), KEY, previous)
