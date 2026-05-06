# Segment Models — Design Decisions

This document records the key design choices made during Sprint 3 for the
segment modeling layer. It covers the data model, feature engineering approach,
embedding strategy, and known limitations.

---

## 1. Segment Definition

A **segment** is a named audience profile defined by:

| Field | Type | Purpose |
|---|---|---|
| `age_range` | `{min_age, max_age}` (optional) | Demographic filter |
| `geo` | `{country, city, region}` (optional) | Geographic filter |
| `category_affinities` | `list[str]` | Behavioral event filter |
| `purchase_history_days` | `int (1–365)` | Lookback window |
| `min_purchase_count` | `int` (optional) | Post-aggregate user filter |
| `min_page_views` | `int` (optional) | Post-aggregate user filter |

**Why JSONB in PostgreSQL:** Segment definitions are heterogeneous (some have
geo, some don't) and expected to evolve. JSONB allows schema evolution without
migrations while still being queryable. The Pydantic model (`SegmentDefinition`)
enforces structure at the application layer.

**What filters do NOT do:** `age_range` and `geo` are stored as metadata
but are not applied against `behavioral_events` because that table does not
contain demographic data (only anonymized behavioral signals). In production,
these would filter against a CRM or registration dataset joined at query time.
For Sprint 3, they are stored for future use and displayed in the UI.

---

## 2. Feature Engineering

Features are computed by aggregating `behavioral_events` rows filtered by:
1. **Time window:** events within the last `purchase_history_days` days.
2. **Category affinity:** events where `payload->>'category'` matches any
   value in `category_affinities` (or all events if the list is empty).

### Computed features per user

| Feature | Formula |
|---|---|
| `purchase_frequency` | `purchase_count / window_days` |
| `avg_basket_size` | `total_spent / max(purchase_count, 1)` |
| `conversion_rate` | `purchase_count / max(session_count, 1)` |
| `session_depth` | `page_view_count / max(session_count, 1)` |
| `category_diversity` | `COUNT(DISTINCT payload->>'category')` |
| `recency_days` | Days since last event (window_days if no activity) |

These 6 features form the numeric vector used to describe a user's
behavioral profile. They are independent of PII — all computed from
anonymized `behavioral_events` rows.

### Idempotency

The feature extraction SQL is read-only. Re-running the Airflow DAG with
the same segment_id will recompute features from the current state of
`behavioral_events` and overwrite the Qdrant point.

---

## 3. Embedding Strategy

### Model: `all-MiniLM-L6-v2`

- **Output dimension:** 384
- **Distance metric:** Cosine similarity
- **Normalization:** L2-normalized embeddings (standard for cosine search)

Model choice is fixed to `all-MiniLM-L6-v2` for consistency with the
OPB AI Mastery Lab stack. Changing the model requires a full re-index
(all segment embeddings must be regenerated).

### What is embedded?

Rather than embedding raw feature vectors (which would require numerical
normalization and lose semantic meaning), we encode a **natural-language
description** of the segment's aggregate behavioral profile:

```
"Segment: Gen Z Madrid. Users: 843. Avg purchase frequency: 0.03/day.
 Avg basket size: $78.50. Avg session depth: 4.2 pages/session.
 Avg category diversity: 1.8 categories. Avg conversion rate: 0.042."
```

This approach:
1. Is robust to missing features (text handles nulls gracefully)
2. Allows free-text similarity queries ("find segments with high electronics
   purchase frequency") without a separate search schema
3. Reuses the sentence-transformer model already in the stack

**Known limitation:** The embedding reflects behavioral patterns, not
demographic similarity. Two segments with identical demographics but
different behavior will have different embeddings — which is the
intended behavior.

---

## 4. Qdrant Collection

- **Collection name:** `persona_segments`
- **Vector size:** 384
- **Distance:** COSINE

Each point payload includes:
```json
{
  "segment_id":          "uuid",
  "segment_name":        "Gen Z Madrid",
  "user_count":          843,
  "window_days":         90,
  "category_affinities": ["Electronics", "Fashion"],
  "text_description":    "...",
  "feature_stats":       {"purchase_frequency_mean": 0.033, ...},
  "embedded_at":         "2026-05-05T10:00:00"
}
```

The `upsert_segment()` call is idempotent — re-indexing a segment replaces
its point rather than creating a duplicate.

---

## 5. Airflow DAG: `extract_segment_data`

The DAG runs four tasks sequentially:

```
get_segment_id → fetch_segment → run_feature_engineering → generate_embedding → update_segment_metadata
```

**Trigger:** Manual only (`schedule=None`). Triggered per-segment via Airflow
UI or REST API with `{"segment_id": "<uuid>"}` in the run config.

**XCom transport:** Task outputs are passed as JSON-serializable dicts
(`SegmentFeatureMatrix.to_dict()` / `from_dict()`). This keeps XCom payloads
small and avoids pickle dependencies.

**On completion:** Sets `last_trained_at = NOW()` and `is_stale = FALSE`
in the `segments` table.

---

## 6. Known Limitations (to address in future sprints)

- `age_range` and `geo` filters are stored but not applied to query results
  (no demographic data in `behavioral_events`). Tracked as technical debt.
- The embedding model (`all-MiniLM-L6-v2`) is loaded fresh on each Airflow
  task run. For production, cache it as an Airflow connection or shared volume.
- No cosine similarity threshold tuning has been done. The default `0.5`
  in `QdrantSegmentStore.search_similar()` is a starting point.
- `_DEFAULT_ORG_ID` in the segments router is hardcoded for Sprint 3.
  Multi-tenancy via JWT claims is deferred to Sprint 9.
