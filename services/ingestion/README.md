# Israeli supermarket price ingestion

## Public sources and verified files

Checked on 2026-11-27. The [price transparency regulations](https://www.chamber.org.il/media/147842/7442.pdf) specify XML and distinguish store directories, full price and promotion files, and intra-day updates. Each adapter follows the publisher's observed layout.

| Publisher | Discovery | Price snapshot | Store directory |
| --- | --- | --- | --- |
| Shufersal | [Public index](https://prices.shufersal.co.il/) and [sortable listing](https://prices.shufersal.co.il/FileObject/?page=1&sort=Branch&sortdir=DESC) | [PriceFull7290027600007-002-098-20261126-030000.gz](https://pricesprodpublic.blob.core.windows.net/pricefull/PriceFull7290027600007-002-098-20261126-030000.gz), 379,421 bytes | [Stores7290027600007-000-20261126-020.gz](https://pricesprodpublic.blob.core.windows.net/stores/Stores7290027600007-000-20261126-020.gz), 12,683 bytes |
| Carrefour Israel | [Main index](https://prices.carrefour.co.il/) embeds the dated directory and file listing in HTML | [PriceFull7290055700007-001-416-20261127-000012.gz](https://prices.carrefour.co.il/20261127/PriceFull7290055700007-001-416-20261127-000012.gz), 908,811 bytes | [Stores7290055700007-000-20261127-000100.xml](https://prices.carrefour.co.il/20261127/Stores7290055700007-000-20261127-000100.xml), 61,394 bytes |

Follow current links from the publisher indexes. Shufersal's links carry temporary query parameters. The table records stable paths and historical files may expire. Carrefour's [separate signage index](https://shilut.carrefour.co.il/) timed out in Sprint 1A. [Rami Levy's transparency page](https://www.rami-levy.co.il/he/price-transparency) links to a [PublishedPrices portal](https://url.retail.publishedprices.co.il/login) that failed TLS hostname verification in Sprint 1A. Neither alternate portal is needed for these adapters.

Sprint 1A verified a separate [878-byte Shufersal delta](https://pricesprodpublic.blob.core.windows.net/price/Price7290027600007-001-001-20261126-230000.gz) with eight accepted rows and a SHA-256 of `43a65c472e8d633791e1499227031a76408041b34e35d608f2b2f842dd4bfd87`. Its item status was populated.

Public publication is mandated. An explicit license for retaining the feeds in bulk, redistributing them, or reusing them commercially remains unverified. Raw files were kept out of the deliverable, and test fixtures are synthetic.

## Observed XML layouts

- Both price samples were gzip-compressed, UTF-8 with a BOM, and used `Root` with `ChainID`, `SubChainID`, `StoreID`, `BikoretNo`, and `Items/Item`. Both had blank `ItemStatus` throughout their full snapshots. Shufersal used second-precision local `PriceUpdateTime` and Carrefour used milliseconds.
- The observed price row fields were `PriceUpdateTime`, `ItemCode`, `LastSaleDateTime`, `ItemType`, `ItemName`, `ManufactureName`, `ManufactureCountry`, `ManufactureItemDescription`, `UnitQty`, `Quantity`, `UnitOfMeasure`, `bIsWeighted`, `QtyInPackage`, `ItemPrice`, `UnitOfMeasurePrice`, `AllowDiscount`, and `ItemStatus`.
- Shufersal's directory was gzip-compressed UTF-8 with a BOM and used a `Chain` root. Carrefour's directory used a `Root` element in plain UTF-16LE XML with a BOM. Both included `ChainID`, `ChainName`, `LastUpdateDate`, and `LastUpdateTime`, followed by `SubChains/SubChain` with `SubChainID`, `SubChainName`, and `Stores/Store`. Store rows contained `StoreID`, `BikoretNo`, `StoreType`, `StoreName`, `Address`, `City`, and `ZIPCode`. The adapters preserve the published city value, which can be a numeric code, and optional street and postal code. The samples contained no coordinates.
- Shufersal published `002/098` in the price header and `2/98` in the directory. The join strips padding on subchain and store IDs for Shufersal only and rejects ambiguous directory keys. Raw IDs are preserved on both records. The Carrefour filename identified `001/416`, while the XML header identified `001/134`. The directory contained `001/416` and had no `001/134`. The production run rejects the file. The default index listed only one PriceFull candidate. The [26 November](https://prices.carrefour.co.il/?date=26/11/2026) and [25 November](https://prices.carrefour.co.il/?date=25/11/2026) requests returned empty price and directory listings when queried.

## Ingestion and validation

Call `ingestion.run.ingest_prices` with a supported source, payload bytes, attempt ID, timezone-aware attempt time, source URL, and feed kind. `ingest_shufersal` remains available to Sprint 1A callers. Supply `expected_store` to verify the price header and scope failures. Pass the publisher's advertised or HTTP content length as `expected_bytes` when available, and report transfer errors with `acquisition_failed=True`, including when a partial buffer exists. The parser checks kind and store identifiers against recognizable file names, parses gzip through its trailer, and exhausts XML before returning observations. It hashes the received bytes and strips URL query, credentials, and fragments from provenance.

A structurally complete snapshot with some invalid rows returns `partial` and the unambiguous accepted rows. Any repeated product key is excluded. An absent key in a partial snapshot or delta is `not_observed`. A successful complete snapshot can report an absent row as `missing`. A missing file is separately identified by the run status. Failed acquisition, malformed XML, and an unverified store mismatch never supply observations. Use the run status as well as the price state before acting on absence. Source status is optional on full snapshots. Zero or negative quantities are rejected because the samples do not establish the meaning of zero. Price comparisons use exact decimal ILS amounts.

Use the publisher adapter's `parse_directory` with bytes and a source URL, then look up the price header through `StoreDirectory.location_for`. Directory results carry source URL and file hash. Missing geography remains absent.

The XML parser decodes in chunks and releases price row elements as it advances, with a 32 MiB decoded XML cap. It retains normalized rows, duplicate keys, and rejection messages to report validation and prevent misleading absence. Memory for these results scales with the number of rows. The runtime uses the Python 3.13 standard library.

## Executed validation

| Snapshot | Total rows | Valid rows | Rejected rows | Unique valid products | Parse time | Traced Python peak | Directory stores | Run status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Shufersal | 7,451 | 7,448 | 3 | 7,448 | 0.481 s | 7.04 MiB | 418 | Partial, store verified |
| Carrefour | 11,084 | 10,925 | 159 | 10,925 | 0.731 s | 10.10 MiB | 147 | Failed filename and header validation |

All row-level rejections in both files were zero quantities. The Carrefour counts are from diagnostic parsing. The production run publishes zero observations for the mismatched file. The unmodified Sprint 1A parser was also executed on the real Shufersal snapshot. It stopped at row 1 because item status was blank, after 0.657 s with tracing enabled and a 64.29 MiB traced peak. Its traced time and the new uninstrumented timings were measured differently.

| Download | SHA-256 |
| --- | --- |
| Shufersal snapshot | `25d3dc66446b58e7c809fc04002cc6576fb5cc8af006fb808578426d24c7a0b1` |
| Shufersal directory | `2f9e23bc766bb559135431aa5059b38ab45a7a478b86d54792f66b65255697ab` |
| Carrefour snapshot | `38612038748e2c77561ff0589ee3251fda48d7a949d3edf6c618af09dcc21b56` |
| Carrefour directory | `487b76670bcc70c4322b894df3b7d58b7b9d94d161ffcc80ca394a4ed82f98c1` |

Next steps are to obtain an identity-consistent Carrefour publication and verify its delta format, clarify zero-quantity semantics with publishers, and confirm reuse terms before automated collection.

## Reproduce verification

With local copies of the observed inputs, run from this directory. The benchmark excludes disk I/O, reports one uninstrumented wall-time pass and a separate Python allocation peak from `tracemalloc`, then parses the directory and checks the store join. Pass the original `--price-url` and `--directory-url` to reproduce filename validation and provenance. The peak excludes the input buffer and process-wide RSS.

```text
python benchmark.py shufersal path/to/PriceFull.gz path/to/Stores.gz
python benchmark.py carrefour path/to/PriceFull.gz path/to/Stores.xml
python -m pytest -q
ruff check .
ruff format --check .
python -m mypy ingestion benchmark.py
```
