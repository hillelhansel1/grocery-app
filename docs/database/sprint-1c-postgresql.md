# Sprint 1C PostgreSQL persistence design

Sprint 1A verified one Shufersal delta with chain, subchain, store, item type, and item code fields, exact decimal prices, and offset-free row timestamps. See the [ingestion evidence and contract](../../services/ingestion/README.md). Sprint 1B had no additional local evidence at the same baseline when this report was written.

Keep exact source files and immutable observations as evidence. Derive one current state per store and source product, plus events for meaningful state transitions. A source product belongs to one publisher and chain. Canonical products and generic product groups are outside this schema.

## Proposed SQL schema

Review draft for a future migration. All external IDs are text to preserve leading zeroes. The source document's normalized scope, version key and order are assigned only under a validated publisher contract. An unresolved file can still be retained as a blob and linked to its acquisition attempt.

```sql
CREATE TABLE retailer (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    publisher text NOT NULL,
    chain_code text NOT NULL,
    UNIQUE (publisher, chain_code)
);

CREATE TABLE store (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    retailer_id bigint NOT NULL REFERENCES retailer,
    subchain_code text NOT NULL,
    store_code text NOT NULL,
    UNIQUE (retailer_id, subchain_code, store_code),
    UNIQUE (retailer_id, id)
);

CREATE TABLE source_product (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    retailer_id bigint NOT NULL REFERENCES retailer,
    item_type text NOT NULL,
    item_code text NOT NULL,
    UNIQUE (retailer_id, item_type, item_code),
    UNIQUE (retailer_id, id)
);

CREATE TABLE source_blob (
    sha256 bytea PRIMARY KEY CHECK (octet_length(sha256) = 32),
    original_bytes bytea NOT NULL
);

CREATE TABLE price_scope (
    store_id bigint PRIMARY KEY REFERENCES store,
    applied_order bigint,
    last_applied_at timestamptz,
    covered_through timestamptz,
    continuity_state text NOT NULL DEFAULT 'unknown'
        CHECK (continuity_state IN ('unknown', 'continuous', 'gap'))
);

CREATE TABLE price_document (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    store_id bigint NOT NULL REFERENCES price_scope,
    kind text NOT NULL CHECK (kind IN ('snapshot', 'delta')),
    publication_key text NOT NULL,
    source_order bigint NOT NULL,
    published_at timestamptz NOT NULL,
    applied_at timestamptz,
    UNIQUE (store_id, publication_key),
    UNIQUE (store_id, source_order),
    UNIQUE (store_id, id)
);

CREATE TABLE document_part (
    document_id bigint NOT NULL REFERENCES price_document,
    part_key text NOT NULL,
    sha256 bytea NOT NULL REFERENCES source_blob,
    PRIMARY KEY (document_id, part_key)
);

CREATE TABLE ingestion_run (
    id uuid PRIMARY KEY,
    expected_store_id bigint REFERENCES store,
    document_id bigint REFERENCES price_document,
    sha256 bytea REFERENCES source_blob,
    source_path text,
    parser_version text NOT NULL,
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    status text NOT NULL CHECK (status IN
        ('started', 'missing', 'failed', 'staged', 'applied', 'duplicate', 'held')),
    diagnostic_code text
);

CREATE TABLE price_observation (
    retailer_id bigint NOT NULL,
    store_id bigint NOT NULL,
    product_id bigint NOT NULL,
    document_id bigint NOT NULL,
    part_key text NOT NULL,
    row_number integer NOT NULL CHECK (row_number > 0),
    amount numeric NOT NULL CHECK (
        amount >= 0 AND amount < 'Infinity'::numeric AND amount = trunc(amount, 2)
    ),
    currency text NOT NULL,
    source_updated_local timestamp NOT NULL,
    item_status text NOT NULL,
    PRIMARY KEY (document_id, part_key, row_number),
    FOREIGN KEY (document_id, part_key) REFERENCES document_part,
    FOREIGN KEY (store_id, document_id) REFERENCES price_document (store_id, id),
    FOREIGN KEY (retailer_id, store_id) REFERENCES store (retailer_id, id),
    FOREIGN KEY (retailer_id, product_id) REFERENCES source_product (retailer_id, id)
);

CREATE TABLE price_current (
    retailer_id bigint NOT NULL,
    store_id bigint NOT NULL,
    product_id bigint NOT NULL,
    state text NOT NULL CHECK (state IN ('present', 'absent')),
    state_document_id bigint NOT NULL,
    observed_document_id bigint NOT NULL,
    observed_part_key text NOT NULL,
    observed_row_number integer NOT NULL,
    PRIMARY KEY (store_id, product_id),
    FOREIGN KEY (store_id, state_document_id) REFERENCES price_document (store_id, id),
    FOREIGN KEY (retailer_id, store_id) REFERENCES store (retailer_id, id),
    FOREIGN KEY (retailer_id, product_id) REFERENCES source_product (retailer_id, id),
    FOREIGN KEY (observed_document_id, observed_part_key, observed_row_number)
        REFERENCES price_observation
);

CREATE TABLE price_event (
    store_id bigint NOT NULL,
    product_id bigint NOT NULL,
    document_id bigint NOT NULL,
    kind text NOT NULL CHECK (kind IN ('first_seen', 'price_changed', 'absent', 'returned')),
    old_amount numeric,
    old_currency text,
    new_amount numeric,
    new_currency text,
    PRIMARY KEY (store_id, product_id, document_id),
    FOREIGN KEY (store_id, product_id) REFERENCES price_current,
    FOREIGN KEY (store_id, document_id) REFERENCES price_document (store_id, id)
);

CREATE INDEX price_current_product_store_idx ON price_current (product_id, store_id);
CREATE INDEX price_document_store_published_idx ON price_document (store_id, published_at DESC);
```

Current price comes from joining its observation pointer for present rows. For absent rows the pointer retains the last reported amount for audit. The apply step must verify that the pointer belongs to the same store and product. Keep current rows as tombstones so event references remain stable. The event's document identifies the transition and witnesses absence. A return with a different amount is a single return event carrying both amounts. Product names, package fields and all unmodeled attributes remain in the original bytes, addressable by part and row. Store-directory payloads can be retained through the same blob and run ledger; normalized directory attributes can be added after its contract is verified.

## Import, ordering and freshness

1. Create an attempt with a stable UUID. Persist downloaded bytes and their SHA-256 before parsing, including malformed or conflicting files. Retain sanitized origin and path, parser version and timestamps. A new network attempt gets a new UUID. Retrying persistence for the same attempt reuses its UUID. Use the hash for byte storage deduplication only. A repeated publication and part with the same hash is a duplicate. A different hash for that identity is a conflict to retain and hold. Distinct publications may legitimately reference identical bytes.
2. Validate store/header, publication identity, part manifest, rows and coverage. Keep every original row in the archived file. For successfully parsed documents, retain each observation under its physical row key. Collapse identical normalized rows for projection only where the adapter permits them, selecting the lowest stable part/row key. Hold conflicting rows for the same product unless a verified publisher rule resolves them. The current Shufersal adapter rejects duplicate product keys, so such files remain raw audit evidence.
3. Lock the store's scope row in the apply transaction. Check the document's application marker after locking. Validate ordering and coverage, then apply current rows, events, scope watermark and the run outcome atomically. An unchanged price advances the observation pointer without emitting an event. Use explicit conflict targets for immutable identities and compare the existing payload or row before treating a conflict as a retry. If a transaction fails, retry from retained bytes. If the commit acknowledgment is lost, the applied marker makes recovery a no-op.
4. Apply a delta only against an established baseline with verified continuity. An omitted item leaves current state and last observation intact. Explicit removal requires verified source semantics. Apply snapshot omissions only after every required part passes validation and the snapshot is authoritative for the entire store price scope. Use a staging anti-join against present rows and write absence transitions once. Failed, partial and missing inputs leave price state untouched. Hold ambiguous precedence and gaps. Archive late files without modifying live state. At a verified later snapshot, coverage can resume from its baseline. To correct historical events, replay accepted evidence into shadow projections, compare and explicitly replace the affected projection. Source order drives projection and row timestamps remain evidence.
5. Keep store coverage, acquisition health and item observation age separate. Advance `covered_through` only with validated coverage. Derive stale status at query time from the covered-through timestamp, a publisher-specific SLA and unresolved gaps. Unknown coverage yields unknown freshness. Report stale prices with their last observation time where allowed and keep them distinguishable from fresh prices and confirmed absences. A recent delta can advance coverage without refreshing untouched rows. Absence describes feed membership. Availability needs its own verified source semantics.

## Indexing and migration

- Start with unpartitioned tables. Primary and unique indexes enforce identity and support staged joins and per-product event lookup. For time-window history, join events to store documents using publication time and measure the plan before adding a document-leading event index. Add a run index on scope and attempt time when operational queries warrant it. Avoid indexing arbitrary raw attributes or computed stale booleans.
- Bulk-load validated rows with `COPY` into staging, then apply set-based joins and upserts. Batch staging and keep promotion atomic per logical publication. Benchmark repeat snapshots, large anti-joins and concurrent stores using representative data. Measure WAL, archive size, autovacuum lag, lock time and query plans. Observation retention and unchanged-row updates add storage and write cost in exchange for replay and precise last-seen evidence. PostgreSQL blob storage keeps a single backup boundary but increases backup and restore volume.
- Partition only after measurement shows a maintenance or query benefit. Consider range partitioning observations by document ID to preserve the existing primary and foreign keys for document-aligned loads. Time partitioning requires carrying its partition key into every parent unique constraint and dependent reference, or maintaining a separate identity ledger. Consider BRIN only for physically correlated range scans. Keep current prices unpartitioned initially. See PostgreSQL's documentation on [partitioning](https://www.postgresql.org/docs/17/ddl-partitioning.html), [bulk loading](https://www.postgresql.org/docs/17/populate.html), [conflict handling](https://www.postgresql.org/docs/17/sql-insert.html), and [BRIN](https://www.postgresql.org/docs/17/brin.html).
- In implementation, pick the supported PostgreSQL major and migration runner, then add versioned schema migrations in dependency order. Replay retained fixtures into an empty local database and verify counts, original-byte hashes, same-file retries, concurrent application, gap handling and snapshot omissions. Backfill chronologically from verified baselines, compare projections and coverage before enabling reads, and keep archived evidence available for rebuild or rollback. Files unavailable as original bytes cannot be claimed as exact historical evidence.

## Sprint 1B evidence gates

| Assumption requiring evidence | Design consequence if unverified |
| --- | --- |
| One authoritative price series per store, with stable chain/subchain/store identifiers and stable chain-wide item type and code | Add a channel/scope key or narrower product namespace if samples show collisions, reassignment or parallel series. Confirm store directories and ID reuse rules. |
| Full-file scope and multipart completeness can be verified, including empty snapshots | Disable omission processing until manifests or equivalent completeness evidence is available. |
| Publications have stable identities, deterministic ordering, gap detection, and a known timezone including DST behavior | Retain raw evidence and hold ambiguous documents. Define correction and precedence rules before advancing coverage. Never use download time or a row timestamp as a publication-order fallback. |
| Item status/removal, duplicates, price precision and currency semantics are consistent across publishers | Preserve source values and gate each adapter. Confirm quantity and unit-price semantics before modeling them in serving tables. |
| Publication cadence, feed outages, expected volume and retention rights | Set freshness thresholds and retention policy only after evidence and review. Size raw storage and indexes using representative full and delta volumes. |
