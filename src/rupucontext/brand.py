"""Rupu branding."""

FAMILY = "rupu"
TOOL = "rupucontext"
TAGLINE = "Lint the pack. Don't pay twice."

METHOD = {
    "unit": "segment_text",
    "exact": "text_exact_v1",
    "normalized": "text_normalized_v1",
    "near": "jaccard_char_shingles_v1",
}

DEFAULT_NEAR_THRESHOLD = 0.85
DEFAULT_SCAN_REPORT = "rupucontext-report.json"
DEFAULT_COMPARE_REPORT = "rupucontext-compare.json"
