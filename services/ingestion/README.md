# Israeli supermarket price ingestion

## Sources checked on 2026-11-27

| Publisher | Endpoint and evidence |
| --- | --- |
| Shufersal | The [public index](https://prices.shufersal.co.il/) links to gzip downloads for store directories (`Stores`), price snapshots (`PriceFull`), price updates (`Price`), and separate promotion snapshots and updates (`PromoFull`, `Promo`). The [sortable listing](https://prices.shufersal.co.il/FileObject/?page=1&sort=Branch&sortdir=DESC) exposes the same categories. Download links use temporary query parameters. Follow a fresh link from the index. |
| Carrefour Israel | The [main index](https://prices.carrefour.co.il/) returned HTTP 200 and embedded a JSON file listing in its HTML. Its JavaScript builds same-origin downloads as `/<published path>/<filename>` using the page's own `path` and file names. The index showed gzip price files. The [separate signage index](https://shilut.carrefour.co.il/) showed plain `Stores…xml` and `Price…gz` in indexed results, but timed out on direct access. Carrefour XML field structure remains unverified. |
| Rami Levy | The [retailer's transparency page](https://www.rami-levy.co.il/he/price-transparency) points to the [PublishedPrices login](https://url.retail.publishedprices.co.il/login). Direct access failed TLS hostname verification. The file URL, compression and XML structure remain unverified. |

The [published Price Transparency Regulations, sections 2–3 and schedules](https://www.chamber.org.il/media/147842/7442.pdf) specify XML, store directories, full price and promotion files and intra-day updates. The schedules describe source fields, including retailer-internal item codes. Treat filenames and XML structure as publisher-specific contracts.

Public access is mandated. No explicit open-data license or grant for bulk retention, redistribution or commercial reuse was verified for these feeds. Confirm applicable source terms and reuse rights before production collection or redistribution. Repository tests use synthetic data.

## Verified Shufersal sample

The [source file path](https://pricesprodpublic.blob.core.windows.net/price/Price7290027600007-001-001-20261126-230000.gz) identifies the 878-byte delta downloaded through the public index. The bare path is provenance and may require a fresh signed query to download. SHA-256 of the gzip payload was `43a65c472e8d633791e1499227031a76408041b34e35d608f2b2f842dd4bfd87`.

The XML had a UTF-8 BOM and `Root/Items/Item` elements. Source headers included `ChainID`, `SubChainID`, `StoreID`, and `BikoretNo`. Row fields included `ItemType`, `ItemCode`, `ItemName`, `Quantity`, `UnitQty`, `ItemPrice`, `PriceUpdateTime`, and `ItemStatus`. The ingestion run accepted 8 of 8 rows, yielding 1 retailer, 1 store, 8 source products and 8 observations. The download was held in memory.

## Package contract

From this directory, import `ingestion.run.ingest_shufersal`. Pass local XML or gzip bytes, an attempt ID, a timezone-aware attempt timestamp, the source URL, and the feed kind from the index. Use `expected_store` to verify the header and scope missing or failed attempts. For no published file, pass `None`. For a transfer error, pass `None` with `acquisition_failed=True`.

Retailer identity is (source, chain ID), store identity adds subchain and store IDs, and product identity adds item type and item code to the retailer. Price comparisons use store and product identity. IDs retain leading zeroes. Observations carry a 1-based XML row and the source's local timestamp as published without an offset. Runs carry the content hash and URL path with authentication and query material removed.

The adapter requires UTF-8, accepts a BOM, preserves exact decimals, and rejects malformed gzip/XML, DTDs, missing or repeated required fields, invalid IDs, negative or sub-cent item prices, nonpositive product quantities, and duplicate product keys. Validation is atomic per file. Additional fields such as package count and unit-price metadata are outside the normalized schema. Item status is retained as a source value.

`price_state` reports unchanged only when a successfully parsed row repeats the prior item amount for that store and product. Absence in a delta is `not_observed`. Absence in a declared snapshot is `missing`. The run status distinguishes a missing input file from a successful snapshot missing a row. Failed ingestion never supplies price observations. These states describe item-price evidence. Item availability, snapshot assembly and historical ordering belong to downstream ingestion.

## Verification

Use Python 3.13. The runtime uses the standard library.

```text
python -m pip install -r requirements-dev.txt
python -m pytest -q
ruff check .
ruff format --check .
python -m mypy ingestion
```

Next steps are to verify a Shufersal full snapshot and store directory, confirm reuse terms, and validate a second publisher's payload before adding an adapter or scheduled ingestion.
