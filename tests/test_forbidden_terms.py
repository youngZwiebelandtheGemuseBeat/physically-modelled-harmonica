from __future__ import annotations

from pathlib import Path


FORBIDDEN_TERMS = [
    "radiation",
    "noise",
    "mixed",
    "body",
    "cover",
    "demo",
    "calibr",
    "sweep",
    "reference",
]


def test_forbidden_terms_do_not_exist_in_minimal_source() -> None:
    project_root = Path(__file__).resolve().parents[1]
    source_root = project_root / "src" / "harmonica_minimal"
    paths = [project_root / "run.py", *source_root.glob("*.py")]
    text = "\n".join(path.read_text().lower() for path in paths)

    for term in FORBIDDEN_TERMS:
        assert term not in text
