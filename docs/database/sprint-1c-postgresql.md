# Sprint 1C PostgreSQL persistence design

Sprint 1A verified one Shufersal delta with chain, subchain, store, item type, and item code fields, exact decimal prices, and offset-free row timestamps. See the [ingestion evidence and contract](../../services/ingestion/README.md). Synthetic Sprint 1B fixtures exercise parser behavior. Publisher semantics require separate evidence.

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
    expected_part_keys text[],
    completeness_evidence text,
    validation_status text NOT NULL DEFAULT 'pending'
        CHECK (validation_status IN ('pending', 'partial', 'conflicted', 'sealed')),
    sealed_at timestamptz,
    applied_at timestamptz,
    rebaselines_after_gap boolean NOT NULL DEFAULT false,
    CHECK ((validation_status = 'sealed') = (sealed_at IS NOT NULL)),
    CHECK (sealed_at IS NULL OR (
        expected_part_keys IS NOT NULL AND cardinality(expected_part_keys) > 0
        AND completeness_evidence IS NOT NULL
    )),
    CHECK (applied_at IS NULL OR sealed_at IS NOT NULL),
    CHECK (NOT rebaselines_after_gap OR (kind = 'snapshot' AND applied_at IS NOT NULL)),
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
    part_key text,
    sha256 bytea REFERENCES source_blob,
    source_path text,
    parser_version text NOT NULL,
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    status text NOT NULL CHECK (status IN
        ('started', 'missing', 'failed', 'partial', 'staged', 'applied', 'duplicate', 'held')),
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
    observed_at timestamptz,
    item_status text,
    PRIMARY KEY (document_id, part_key, row_number),
    UNIQUE (store_id, product_id, document_id, part_key, row_number),
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
    FOREIGN KEY (store_id, product_id, observed_document_id, observed_part_key, observed_row_number)
        REFERENCES price_observation (store_id, product_id, document_id, part_key, row_number)
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
    follows_coverage_gap boolean NOT NULL DEFAULT false,
    CHECK ((old_amount IS NULL) = (old_currency IS NULL)),
    CHECK ((new_amount IS NULL) = (new_currency IS NULL)),
    CHECK (
        (kind = 'first_seen' AND old_amount IS NULL AND new_amount IS NOT NULL)
        OR (kind = 'price_changed' AND old_amount IS NOT NULL AND new_amount IS NOT NULL
            AND (old_amount, old_currency) IS DISTINCT FROM (new_amount, new_currency))
        OR (kind = 'absent' AND old_amount IS NOT NULL AND new_amount IS NULL)
        OR (kind = 'returned' AND old_amount IS NOT NULL AND new_amount IS NOT NULL)
    ),
    PRIMARY KEY (store_id, product_id, document_id),
    FOREIGN KEY (store_id, product_id) REFERENCES price_current,
    FOREIGN KEY (store_id, document_id) REFERENCES price_document (store_id, id)
);

CREATE INDEX price_current_product_store_idx ON price_current (product_id, store_id);
CREATE INDEX price_document_store_published_idx ON price_document (store_id, published_at DESC);
```

Current price comes from its observation pointer. The composite foreign key enforces store and product agreement during live apply, backfill and replay. Absent rows retain the last observation for audit and remain as tombstones so event references stay stable. Product attributes remain in original bytes, addressable by part and row. Store-directory payloads can use the same blob and run ledger.

## Import, ordering and freshness

1. **Acquire.** Persist exact bytes and SHA-256 before parsing, including malformed or conflicting files. Record sanitized source location, part key when known, parser version and timestamps. Reuse the attempt UUID when retrying its persistence and assign a new UUID for a new acquisition. Hash equality deduplicates storage. A repeated publication and part with the same hash can still require application. Distinct publications may share bytes. Retain differing bytes for the same part as a conflict, linked to the attempt. Preserve original rows and key normalized observations by physical row address. Collapse identical rows for projection only under a verified publisher rule. Hold unresolved conflicts.
2. **Validate and seal.** Persist the expected part keys and the evidence used to derive them, such as an archived manifest reference or a versioned single-file contract. Store successfully validated parts in `document_part`. Serialize accepted-part registration, conflict decisions and sealing under the store's scope lock. Seal only after the accepted set exactly matches the expected set and the combined document passes scope, row, and duplicate checks. Seal accepted hashes and normalized rows as immutable. A zero-row snapshot requires positive evidence of authoritative coverage and a valid empty result under that publisher's contract. Row count alone establishes neither. Partial and conflicted snapshots cannot advance coverage or remove prices. A conflict received after sealing is held for reconciliation and suspends coverage extension if continuity is uncertain.
3. **Apply.** Under the same scope lock, check the sealed publication's `applied_at`. In one transaction apply observations to current state, emit events, and commit the applied marker, scope watermarks and run outcome. Snapshot omissions use an anti-join against present rows. Use explicit conflict targets and compare existing content on retries. A `staged` run has durable validated input awaiting application. `partial` means only some required inputs or rows passed validation. `failed` records an acquisition, validation or apply error. `held` records an ordering or evidence blocker. `applied` records committed projection work. After rollback, record failure separately and retry from durable input. After an ambiguous commit, recheck the marker under lock before changing status or retrying. Use `duplicate` only after confirming that the matching publication was already applied.
4. **Order and reconcile.** Apply deltas in verified publisher order after a sealed baseline. A delta omission leaves current state and last observation intact. Explicit removal requires verified semantics. On an unverified gap, record it under the scope lock, suspend coverage extension, and hold dependent deltas without advancing the coverage watermark. A late delta ahead of the applied watermark can fill the gap and release held deltas in order once continuity is verified. Files at or behind the watermark cannot alter live state through normal apply. A later authoritative snapshot can rebaseline coverage from its own publication and leave the earlier history gap visible. For historical corrections, rebuild from accepted evidence into shadow projections using the same constraints, then lock the scope, verify the captured applied watermark and accepted input set are still current, and atomically cut over current state, events and coverage. Catch up or rebuild if live imports advanced during replay.

### Price events

Compare the exact amount and currency for present-to-present observations. A repeated identical pair advances the observation pointer without an event. A first sighting records the new pair, a change records both pairs, and an absence records the prior pair. A return records the last known pair and the new pair in one event. Mark the snapshot `rebaselines_after_gap` even if every price matches. For transitions detected at that snapshot, set `follows_coverage_gap` and date the detection to that publication. The actual transition time during the gap remains unknown.

### 48-hour eligibility

Evaluate eligibility at a single query timestamp. For a present product, start with `price_observation.observed_at`, the verified instant when the publisher explicitly attested to that row's price. Use publication time for this only when the verified contract supports that interpretation. Retain the original local row timestamp separately. Acquisition and apply timestamps measure ingestion health and never qualify a price.

Use `covered_through` to extend an explicit observation only when documented publisher evidence establishes that every price-affecting change would appear in the covered series and the applied chain is verified contiguous from that observation through the watermark. Use the later of the explicit observation and this eligible coverage watermark. A recent delta alone leaves omitted products' explicit observation times unchanged. During an unverified gap, fall back to explicit observation until continuity is restored or a verified snapshot supplies a new baseline.

A present price qualifies only when its effective timestamp is known and `0 <= query_time - effective_timestamp < interval '48 hours'`. At exactly 48 elapsed hours it expires. Future timestamps yield unknown eligibility. Exclude expired, unknown and absent prices from basket optimization. Expired or unknown last-known prices may be shown as stale with their last verified observation timestamp when available. Label an unknown observation time explicitly.

## Indexing and migration

- Start with unpartitioned tables. Primary and unique indexes enforce identity and support staged joins and per-product event lookup. For time-window history, join events to store documents using publication time and measure the plan before adding a document-leading event index. Add a run index on scope and attempt time when operational queries warrant it. Avoid indexing arbitrary raw attributes or computed stale booleans.
- Bulk-load validated rows with `COPY` into staging, then apply set-based joins and upserts. Batch staging and keep promotion atomic per logical publication. Benchmark repeat snapshots, large anti-joins and concurrent stores using representative data. Measure WAL, archive size, autovacuum lag, lock time and query plans. Observation retention and unchanged-row updates add storage and write cost in exchange for replay and precise last-seen evidence. PostgreSQL blob storage keeps a single backup boundary but increases backup and restore volume.
- Partition only after measurement shows a maintenance or query benefit. Consider range partitioning observations by document ID to preserve the existing primary and foreign keys for document-aligned loads. Time partitioning requires carrying its partition key into every parent unique constraint and dependent reference, or maintaining a separate identity ledger. Consider BRIN only for physically correlated range scans. Keep current prices unpartitioned initially. See PostgreSQL's documentation on [partitioning](https://www.postgresql.org/docs/17/ddl-partitioning.html), [bulk loading](https://www.postgresql.org/docs/17/populate.html), [conflict handling](https://www.postgresql.org/docs/17/sql-insert.html), and [BRIN](https://www.postgresql.org/docs/17/brin.html).
- In implementation, pick the supported PostgreSQL major and migration runner, then add versioned schema migrations in dependency order. Replay retained fixtures into an empty local database and verify counts, original-byte hashes, same-file retries, concurrent application, gap handling and snapshot omissions. Backfill chronologically from verified baselines, compare projections and coverage before enabling reads, and keep archived evidence available for rebuild or rollback. Files unavailable as original bytes cannot be claimed as exact historical evidence.
- Retention must follow current pointers, including tombstones, through observations, accepted parts and original blobs. Preserve event documents, run provenance, and evidence needed for supported replay windows. Before retiring data or detaching a future partition, verify that live foreign keys and replay requirements are satisfied.

## Sprint 1B evidence gates

| Assumption requiring evidence | Design consequence if unverified |
| --- | --- |
| One authoritative price series per store, with stable chain/subchain/store identifiers and stable chain-wide item type and code | Add a channel/scope key or narrower product namespace if samples show collisions, reassignment or parallel series. Confirm store directories and ID reuse rules. |
| Full-file scope and multipart completeness can be verified, including empty snapshots | Disable omission processing until manifests or equivalent completeness evidence is available. |
| Publications have stable identities, deterministic ordering, gap detection, and a known timezone including DST behavior | Retain raw evidence and hold ambiguous documents. Define correction and precedence rules before advancing coverage. Never use download time or a row timestamp as a publication-order fallback. |
| Row or publication timestamps attest to the reported price, and the update series reports every price-affecting change | Leave explicit observation time unknown when no trusted clock exists. Disable coverage-based extension until the publisher guarantee and contiguous coverage can be verified. |
| Item status can be missing, and removals, duplicates, precision and currency have documented semantics | Preserve source values and gate each adapter. Synthetic fixtures establish parser behavior only. |
| Publication cadence, feed outages, expected volume and retention rights | Set feed-health thresholds and retention policy after evidence and review. The 48-hour basket eligibility cutoff applies independently of feed cadence. |

## Acceptance-test matrix

Use synthetic fixtures with explicitly declared contracts for these tests. Validate real publisher contracts separately.

| Case | Expected result |
| --- | --- |
| Current row points to an observation for a different store or product | Composite FK rejects live apply, backfill and replay. |
| Apply fails after staging, then the same bytes are retried | First transaction leaves no projection or watermark changes. Retrying applies once. Retrying after a lost commit acknowledgment creates no duplicate event. |
| Snapshot is missing a part, has a conflicting hash, or contains zero rows with unknown completeness | Preserve downloaded evidence. Keep accepted state and watermarks unchanged. |
| A verified authoritative empty snapshot is sealed | All previously present offers in scope become absent once. |
| A delta omits an item, then a late delta fills an order gap | The omission leaves its observation unchanged. While the gap is unresolved, hold dependent deltas and suspend coverage extension. Verify continuity and drain held deltas in order. A late file behind the applied watermark requires replay. |
| An eligible price is just under 48 hours old, exactly 48 hours old, or has an unknown timestamp | The first qualifies. The second and third are excluded from optimization. An omitted row gets an extension only with verified publisher evidence and contiguous coverage. |
| Same amount and currency, currency-only change, or changed price at post-gap rebaseline | Same pair advances the pointer without an event. A currency change emits one event. The post-gap event carries both pairs and marks detection at rebaseline. |
| Live apply advances during replay, or retention targets a referenced observation | Replay cutover waits for catch-up or rebuild. Retention preserves the observation and its raw provenance. |
