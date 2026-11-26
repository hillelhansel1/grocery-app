from datetime import UTC, datetime
from gzip import compress

import pytest

from ingestion import carrefour, shufersal
from ingestion.models import FeedKind, PriceState, Retailer, RunStatus, Store
from ingestion.run import ingest_prices, price_state

# Synthetic fixtures reproducing the relevant fields of the verified publisher layouts.
ITEM = """
<Item><ItemCode>00042</ItemCode><ItemType>1</ItemType><ItemName>לחם</ItemName>
<UnitQty>kg</UnitQty><Quantity>1</Quantity><ItemPrice>3.20</ItemPrice>
<PriceUpdateTime>2026-11-27T01:02:03.120</PriceUpdateTime><ItemStatus /></Item>
"""
PRICE = """
<Root><ChainID>7290055700007</ChainID><SubChainID>001</SubChainID>
<StoreID>416</StoreID><Items>{items}</Items></Root>
"""
STORES = """
<{root}><ChainID>7290055700007</ChainID><ChainName>רשת</ChainName>
<SubChains><SubChain><SubChainID>001</SubChainID><Stores>
<Store><StoreID>416</StoreID><StoreName>סניף</StoreName>
<Address>דרך 1</Address><City>7100</City><ZIPCode>0012345</ZIPCode></Store>
<Store><StoreID>417</StoreID><StoreName>אחר</StoreName></Store>
</Stores></SubChain></SubChains></{root}>
"""
STORE = Store(Retailer("carrefour", "7290055700007"), "001", "416")
URL = "https://example.invalid/PriceFull7290055700007.gz"


def ingest(payload, **kwargs):
    return ingest_prices(
        payload,
        source="carrefour",
        source_url=kwargs.pop("source_url", URL),
        attempted_at=datetime(2026, 11, 27, tzinfo=UTC),
        run_id="sample",
        kind=kwargs.pop("kind", FeedKind.SNAPSHOT),
        expected_store=STORE,
        **kwargs,
    )


def test_carrefour_price_and_utf16_store_directory_match():
    result = ingest(compress(PRICE.format(items=ITEM).encode("utf-8-sig")))
    assert result.status == RunStatus.SUCCESS
    (price,) = result.observations
    assert price.item_status is None
    assert price.source_updated_at.microsecond == 120000
    directory = carrefour.parse_directory(
        STORES.format(root="Root").encode("utf-16"), URL
    )
    assert directory.retailer == STORE.retailer
    assert directory.retailer_name == "רשת"
    location = directory.location_for(price.store)
    assert location is not None
    assert (location.name, location.address, location.city, location.postal_code) == (
        "סניף",
        "דרך 1",
        "7100",
        "0012345",
    )
    assert directory.locations[1].address is None
    assert directory.locations[1].city is None


def test_shufersal_dir_uses_chain_root_and_utf8():
    directory = shufersal.parse_directory(
        STORES.format(root="Chain").encode("utf-8-sig"), URL
    )
    assert directory.retailer.source == "shufersal"
    assert len(directory.locations) == 2
    assert directory.location_for(STORE) is None
    with pytest.raises(ValueError, match="Chain/SubChains"):
        shufersal.parse_directory(STORES.format(root="Root").encode(), URL)


@pytest.mark.parametrize(
    "change",
    [
        lambda xml: xml.replace("<StoreID>417", "<StoreID>416"),
        lambda xml: xml.replace("<StoreName>סניף</StoreName>", ""),
        lambda xml: xml.replace("<Stores>", "<Stores><Unexpected />"),
    ],
)
def test_directory_rejects_duplicate_or_malformed_stores(change):
    with pytest.raises(ValueError):
        carrefour.parse_directory(
            change(STORES.format(root="Root")).encode("utf-16"), URL
        )


def test_snapshot_rejections_preserve_good_rows_without_claiming_absence():
    malformed = ITEM.replace("00042", "00043").replace("<Quantity>1", "<Quantity>0")
    result = ingest(PRICE.format(items=ITEM + malformed).encode())
    assert result.status == RunStatus.PARTIAL
    assert len(result.observations) == len(result.rejected) == 1
    assert result.rejected[0].startswith("row 2: Quantity")
    assert price_state(result, STORE, ("1", "00043")) == PriceState.NOT_OBSERVED


@pytest.mark.parametrize(
    "mode", ["length", "gzip", "xml", "transport", "kind", "encoding"]
)
def test_incomplete_or_wrong_snapshot_has_no_observations(mode):
    payload = PRICE.format(items=ITEM).encode()
    if mode == "length":
        result = ingest(payload, expected_bytes=len(payload) + 1)
    elif mode == "gzip":
        result = ingest(compress(payload)[:-4])
    elif mode == "xml":
        result = ingest(payload[:-12])
    elif mode == "transport":
        result = ingest(payload, acquisition_failed=True)
    elif mode == "kind":
        result = ingest(payload, kind=FeedKind.DELTA)
    else:
        result = ingest(payload.replace(b"3.20", b"\xff"))
    assert result.status == RunStatus.FAILED
    assert not result.observations
    assert price_state(result, STORE, ("1", "00042")) == PriceState.FAILED


def test_duplicate_rows_never_supply_ambiguous_prices():
    other = ITEM.replace("00042", "00043")
    result = ingest(PRICE.format(items=ITEM + other + ITEM).encode())
    assert result.status == RunStatus.PARTIAL
    assert len(result.rejected) == 2
    assert [row.product.item_code for row in result.observations] == ["00043"]
    assert price_state(result, STORE, ("1", "00042")) == PriceState.NOT_OBSERVED


def test_shufersal_directory_join_preserves_source_padding():
    xml = STORES.format(root="Chain").replace("<SubChainID>001", "<SubChainID>1")
    xml = xml.replace("<StoreID>416", "<StoreID>0416")
    directory = shufersal.parse_directory(xml.encode(), URL)
    matched = directory.location_for(Store(directory.retailer, "001", "416"))
    assert matched is not None
    assert (matched.store.subchain_id, matched.store.store_id) == ("1", "0416")
    with pytest.raises(ValueError, match="duplicate store"):
        shufersal.parse_directory(
            xml.replace("<StoreID>417", "<StoreID>416").encode(), URL
        )


def test_price_filename_store_mismatch_fails_closed():
    result = ingest(
        PRICE.format(items=ITEM).encode(),
        source_url="https://example.invalid/PriceFull7290055700007-001-999-20261127.gz",
    )
    assert result.status == RunStatus.FAILED
    assert result.error == "price header identifiers do not match filename"
    assert not result.observations
