from __future__ import annotations

from pathlib import Path


FORBIDDEN_TERMS = [
    "radiation",
    "body resonance",
    "noise synthesis",
    "mixed output",
    "demo renderer",
    "calibration",
    "sweep",
    "reference comparison",
]


def test_forbidden_terms_do_not_exist_in_minimal_source() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src" / "harmonica_minimal"
    text = "\n".join(path.read_text().lower() for path in source_root.glob("*.py"))

    for term in FORBIDDEN_TERMS:
        assert term not in text

