# RupuContext

Part of the **RupuData** family.

**Lint the pack. Don't pay twice.**

Local-first CLI to audit LLM context packs for duplicate chunks, cross-segment overlap, and wasted context. Deterministic JSON reports. CI gates. No model calls.

**Repo:** [`rupucontext`](https://github.com/EmanuelCorreaAR/rupucontext) · **License:** Apache 2.0

---

## The question

**RupuData** asks: does your train overlap with your eval?

**RupuContext** asks: are you paying the model to read the same text twice?

You don't train anymore — you rent an LLM. The cost isn't fine-tuning; it's the **context pack** sent on every call: system prompt, retrieved chunks, history, user message. Duplicate chunks. Policy pasted again in the RAG. Questions already in the KB. The invoice arrives later. **RupuContext looks before the call.**

Local. JSONL in. Deterministic JSON out. CI gate (exit 2). Technical signals — not certification, not a dashboard, not a proxy, not another LLM call to "evaluate."

---

## What it compares

Text overlap — exact match, normalized match, Jaccard shingles. Same engine as RupuData; different object: the **pack you send to the LLM**, not the training dataset.

| | RupuData | RupuContext |
|---|----------|-------------|
| Question | Does train overlap eval? | Are you buying the same context twice? |
| Input | Corpus / benchmark | Context pack (JSONL) |
| User | ML / data eng | Agent / RAG eng with exportable traces |

**Family:** `rupudata` = path of the data · `rupucontext` = path of the context.

---

## What it is not

- Not token pricing (no tiktoken, no USD, no `--max-input-tokens` billing gates)
- Not "don't call the LLM" — that's invoice logic, not leakage detection
- Not tabular data tooling
- Not prompt versioning
- Not [Helicone](https://helicone.ai) or an observability proxy

If you can't export a pack or a trace, you're not the user yet.

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

## CLI (planned v0.1)

```bash
pip install rupucontext

rupucontext scan pack.jsonl                    # parse, validate, summarize
rupucontext compare corpus.jsonl q.jsonl       # overlap: corpus vs questions
rupucontext report pack.jsonl -o out.json
rupucontext gate pack.jsonl --threshold 0.85   # exit 2 if overlap exceeds threshold
```

---

## Report (deterministic JSON)

```json
{
  "pack_id": "req-001",
  "duplicates": [
    {"a": "c42", "b": "c17", "method": "exact", "overlap": 1.0}
  ],
  "cross_segment": [
    {"from": "retrieve", "to": "system", "overlap": 0.82}
  ],
  "summary": {
    "segment_count": 4,
    "duplicate_bytes": 4096
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
| `2` | Gate failed — duplicate/overlap above threshold |

```yaml
# .github/workflows/rupucontext.yml
- run: rupucontext gate fixtures/dup-pack.jsonl --threshold 0.85
```

---

## Status

Early stage. Skeleton repo — CLI implementation in progress.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).
