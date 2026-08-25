# RupuContext

**Lint the pack. Don't pay twice.**

Part of the **[RupuData](https://github.com/EmanuelCorreaAR/rupudata)** family — same overlap methodology, different object.

| | **RupuData** | **RupuContext** |
|---|---|---|
| Tagline | Follow the path of your data. | Lint the pack. Don't pay twice. |
| Question | Does my training data overlap with my eval? | Am I paying the model to read the same text twice? |
| Input | Dataset / benchmark (JSONL) | Context pack (JSONL segments) |
| User | ML / data eng | Agent / RAG eng with exportable traces |

RupuContext answers an uncomfortable question for the LLM era: **are you sending duplicate chunks, repeated policy text, or KB content twice in the same context pack?**

Local CLI. Deterministic JSON audit reports. Policy gates for CI. Technical signals — not certification, not token pricing, not another LLM call to "evaluate."

**Repo:** [`rupucontext`](https://github.com/EmanuelCorreaAR/rupucontext) · **Sibling:** [`rupudata`](https://github.com/EmanuelCorreaAR/rupudata) · **License:** Apache 2.0

---

## Install

Requires Python 3.9+.

```bash
pip install rupucontext
rupucontext --help
```

---

## Quick start

```bash
rupucontext scan fixtures/dup-pack.jsonl
rupucontext report fixtures/dup-pack.jsonl
rupucontext compare fixtures/corpus.jsonl fixtures/questions.jsonl
rupucontext report fixtures/dup-pack.jsonl --fail-on-overlap
rupucontext report fixtures/dup-pack.jsonl --max-overlap-rate 0.85
rupucontext gate fixtures/dup-pack.jsonl --threshold 0.85
```

Policy gates (`--fail-on-overlap`, `--max-overlap-rate`, `gate`) exit **2** when thresholds are exceeded. Exit **1** is reserved for errors. The JSON audit report (including gate) is written either way.

---

## Input format (JSONL)

One line per segment. Group by `pack_id`:

```jsonl
{"pack_id": "req-001", "role": "system", "text": "You are a helpful assistant..."}
{"pack_id": "req-001", "role": "retrieve", "chunk_id": "c42", "text": "Refund policy: items within 30 days..."}
{"pack_id": "req-001", "role": "retrieve", "chunk_id": "c17", "text": "Refund policy: items within 30 days..."}
{"pack_id": "req-001", "role": "user", "text": "Can I return this?"}
```

Roles: `system`, `retrieve`, `history`, `user` (extensible). `chunk_id` optional but recommended for retrieve segments.

---

## Matching methodology (shared with RupuData)

Same family engine — different audit object:

| Mode | Unit | Method id |
|------|------|-----------|
| Exact | segment `text` | `text_exact_v1` |
| Normalized | segment `text` | `text_normalized_v1` |
| Near-duplicate | character shingles | `jaccard_char_shingles_v1` |

RupuData flags train/eval leakage. RupuContext flags wasted context inside the pack you send on every LLM call.

---

## Audit report (deterministic JSON)

```json
{
  "tool": "rupucontext",
  "version": "0.1.0",
  "family": "rupudata",
  "tagline": "Lint the pack. Don't pay twice.",
  "command": "report",
  "methodology": {
    "exact": "text_exact_v1",
    "normalized": "text_normalized_v1",
    "near": "jaccard_char_shingles_v1"
  },
  "result": {
    "pack_id": "req-001",
    "duplicates": [
      {"a": "c42", "b": "c17", "method": "exact", "overlap": 1.0}
    ],
    "cross_segment": [],
    "summary": {
      "segment_count": 4,
      "duplicate_bytes": 65
    }
  },
  "gate": {
    "passed": false,
    "rules": [
      {"metric": "max_overlap_rate", "actual": 1.0, "threshold": 0.85, "passed": false}
    ]
  }
}
```

Byte counts and overlap ratios — not token estimates.

---

## Exit codes (CI gate)

| Code | Meaning |
|------|---------|
| `0` | Pass — no overlap above threshold |
| `1` | Usage error — invalid file or schema |
| `2` | Policy gate failed — duplicate/overlap above threshold |

```yaml
# .github/workflows/rupucontext.yml
- run: rupucontext gate fixtures/dup-pack.jsonl --threshold 0.85
```

---

## Try the fixtures

```bash
git clone https://github.com/EmanuelCorreaAR/rupucontext.git
cd rupucontext
pip install -e ".[dev]"

rupucontext report fixtures/dup-pack.jsonl          # exact duplicate c42 ↔ c17
rupucontext report fixtures/clean-pack.jsonl        # no overlap above threshold
rupucontext compare fixtures/corpus.jsonl fixtures/questions.jsonl
rupucontext gate fixtures/dup-pack.jsonl --threshold 0.85   # exit 2
```

---

## What it is not

- Not token pricing (no tiktoken, no USD)
- Not prompt versioning or observability proxy
- Not semantic / paraphrase matching (same as RupuData v0.9 — on purpose)

If you can't export a pack or a trace, you're not the user yet.

---

## Development

```bash
git clone https://github.com/EmanuelCorreaAR/rupucontext.git
cd rupucontext
pip install -e ".[dev]"
pytest
```

---

## Status

**0.1.0** — CLI (`scan`, `compare`, `report`, `gate`); shared overlap methodology with RupuData; policy gates; fixtures and CI.

**Next:** stabilize the audit contract toward 1.0; optional cross-segment evidence samples in terminal output.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).
