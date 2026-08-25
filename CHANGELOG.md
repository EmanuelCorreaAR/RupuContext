# Changelog

## [0.1.1] - 2026-08-25
### Fixed
- PyPI wheel packaging: include the `rupucontext` package (0.1.0 wheel shipped metadata only)

## [0.1.0] - 2026-08-25

### Added
- CLI `rupucontext scan` — audit a context pack (JSONL segments) for wasted overlap
- CLI `rupucontext compare` — corpus vs user-question overlap (RAG leak signal)
- Matching on segment `text`: `text_exact_v1`, `text_normalized_v1`, `jaccard_char_shingles_v1` (`method.unit=segment_text`)
- `scan` findings: retrieve∩retrieve duplicates (`exact_duplicates`, `near_duplicates`) and cross-role overlap (`cross_segment` with `from`, `to`, `method`, `overlap`)
- Quality **policy gates** for CI: `--fail-on-overlap`, `--max-duplicate-rate`, `--max-near-duplicate-rate` (scan), `--max-overlap-rate` (compare)
- Optional top-level `gate` object (`passed` + `rules[]` with metric/threshold/actual)
- Deterministic audit JSON: `input → configuration → method → result → (optional) gate`
- `result.results[]` always — one object per `pack_id` (stable contract for parsers)
- `duplicate_rate` / `record_rate` over **retrieve segments only** (`rate_denominator: retrieve_segments`)
- Rich terminal summary; default reports `rupucontext-report.json` / `rupucontext-compare.json`
- Fixtures: `dup-pack`, `clean-pack`, `policy-twice`, `corpus`, `questions`
- Technical audit contract in `docs/AUDIT.md`
- GitHub Actions CI: pytest on Python 3.9–3.12; gate smoke on clean/dup fixtures
### Changed
- Exit code `2` means configured policy failure; exit `1` is reserved for I/O and usage errors
