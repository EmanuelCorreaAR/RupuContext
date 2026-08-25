# RupuContext

**Lint the pack. Don't pay twice.**

Part of the **Rupu** family.

Local CLI. Deterministic JSON audit reports. Policy gates for CI. Technical signals — not certification, not token pricing, not another LLM call to "evaluate."


## Install

Requires Python 3.9+.

```bash
pip install rupucontext
rupucontext --help
```


## Quick start

```bash
rupucontext scan fixtures/dup-pack.jsonl
rupucontext scan fixtures/dup-pack.jsonl --fail-on-overlap
rupucontext compare fixtures/corpus.jsonl fixtures/questions.jsonl
```

Policy gates exit **2** when thresholds are exceeded. Exit **1** is reserved for errors. The JSON audit report (including gate) is written either way.


## Commands

| Command | Role |
|---------|------|
| `scan pack.jsonl` | Duplicates inside the pack |
| `compare corpus.jsonl questions.jsonl` | RAG leak signal (eval text in the KB) |

Gates are flags, not subcommands:

| Flag | Command | Meaning |
|------|---------|---------|
| `--fail-on-overlap` | scan, compare | Exit 2 if any overlap is found |
| `--max-duplicate-rate` | scan | Exit 2 if exact `duplicate_rate` exceeds threshold |
| `--max-near-duplicate-rate` | scan | Exit 2 if near-duplicate `record_rate` exceeds threshold |
| `--max-overlap-rate` | compare | Exit 2 if overlap rate exceeds threshold |

`--near-duplicate-threshold` (default `0.85`) controls **detection** of near-duplicates. Policy gates use **rates**, not the Jaccard cutoff.


## Input format (JSONL)

One line per segment. Group by `pack_id`:

```jsonl
{"pack_id": "req-001", "role": "system", "text": "You are a helpful assistant..."}
{"pack_id": "req-001", "role": "retrieve", "chunk_id": "c42", "text": "Refund policy: items within 30 days..."}
{"pack_id": "req-001", "role": "retrieve", "chunk_id": "c17", "text": "Refund policy: items within 30 days..."}
{"pack_id": "req-001", "role": "user", "text": "Can I return this?"}
```

Roles: `system`, `retrieve`, `history`, `user` (extensible). `chunk_id` optional but recommended for retrieve segments.


## Audit report

Reports follow: `input → configuration → method → result → (optional) gate`.

```json
{
  "tool": "rupucontext",
  "version": "0.1.0",
  "command": "scan",
  "input": {
    "path": "fixtures/dup-pack.jsonl",
    "segments": 4,
    "packs": 1
  },
  "configuration": {
    "near_duplicate_threshold": 0.85,
    "fail_on_overlap": true
  },
  "method": {
    "unit": "segment_text",
    "exact": "text_exact_v1",
    "normalized": "text_normalized_v1",
    "near": "jaccard_char_shingles_v1"
  },
  "result": {
    "pack_id": "req-001",
    "segment_count": 4,
    "exact_duplicates": {
      "pairs": 1,
      "segments_flagged": 2,
      "duplicate_bytes": 65,
      "duplicate_rate": 0.5,
      "evidence": [
        {"a": "c42", "b": "c17", "method": "exact", "overlap": 1.0}
      ]
    },
    "near_duplicates": {
      "pairs": 0,
      "segments_flagged": 0,
      "record_rate": 0.0,
      "evidence": []
    },
    "cross_segment": []
  },
  "gate": {
    "passed": false,
    "rules": [
      {"metric": "overlap_pairs", "actual": 1, "threshold": 0, "passed": false}
    ]
  }
}
```

Byte counts and overlap ratios — not token estimates. Contract details: [docs/AUDIT.md](docs/AUDIT.md).


## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success (no policy failure) |
| `1` | Usage error — invalid file or schema |
| `2` | Policy gate failed |

```yaml
# .github/workflows/rupucontext.yml
- run: rupucontext scan fixtures/dup-pack.jsonl --fail-on-overlap
```


## What it is not

- Not token pricing (no tiktoken, no USD)
- Not prompt versioning or observability proxy
- Not semantic / paraphrase matching (on purpose)

If you can't export a pack or a trace, you're not the user yet.


## Development

```bash
git clone https://github.com/EmanuelCorreaAR/rupucontext.git
cd rupucontext
pip install -e ".[dev]"
pytest
```


## Status

**0.1.0** — `scan` + `compare`; policy gate flags; deterministic audit JSON.

**Next:** stabilize audit contract toward 1.0.


## License

Apache License 2.0
