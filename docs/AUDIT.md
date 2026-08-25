# Technical audit contract

RupuContext JSON reports follow:

```text
input → configuration → method → result → (optional) gate
```

Defaults: `rupucontext-report.json` (scan), `rupucontext-compare.json` (compare).

Reports are **technical signals, not legal certification.**

## Matching model

| `method.unit` | Text source | Specs |
|---------------|-------------|--------|
| `segment_text` | segment `text` field | `text_exact_v1` / `text_normalized_v1` / `jaccard_char_shingles_v1` |

Near-duplicate detection uses character shingles (Jaccard). `--near-duplicate-threshold` controls detection only.

## Scan result vocabulary

| Field | Meaning |
|-------|---------|
| `exact_duplicates.pairs` | Segment pairs with exact or normalized match |
| `exact_duplicates.duplicate_rate` | `segments_flagged / segment_count` |
| `near_duplicates.pairs` | Segment pairs above Jaccard threshold |
| `near_duplicates.record_rate` | Near-flagged segments / segment count |
| `cross_segment` | Best overlap between role groups |

Evidence documents **which segments** and **which score** — not full text payloads.

## Compare result vocabulary

| Field | Meaning |
|-------|---------|
| `exact_overlap.shared_segments` | Question segments matching corpus |
| `exact_overlap.rate` | `shared_segments / question_segments` |
| `matches.exact` | Evidence pairs |

## Policy gates

`gate` is omitted when no policy flags are set.

| Flag | Command | Metrics |
|------|---------|---------|
| `--fail-on-overlap` | scan, compare | any overlap must be zero |
| `--max-duplicate-rate` | scan | `exact_duplicates.duplicate_rate` |
| `--max-near-duplicate-rate` | scan | `near_duplicates.record_rate` |
| `--max-overlap-rate` | compare | `exact_overlap.rate` |

A rule **passes** when `actual <= threshold`.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success (no policy failure) |
| `1` | I/O or usage error |
| `2` | Configured quality gate failed |

Without policy flags, findings are reported and the process exits `0`.
