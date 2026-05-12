import pytest
from extractors.tools.tag_normalization import canonicalize_tag, canonicalize_tags
@pytest.mark.parametrize("raw, expected", [
    ("PostgreSQL", "postgresql"),
    ("Postgres DB", "postgres-db"),
    ("  RAG ", "rag"),
    ("machine_learning", "machine-learning"),
    ("Retrieval-Augmented Generation", "retrieval-augmented-generation"),
    ("the", None),
    ("book", None),
    ("introduction", None),
    ("", None),
    ("a", None),
    ("é" * 81, None),
])
def test_canonicalize_tag(raw, expected):
    assert canonicalize_tag(raw) == expected
def test_canonicalize_tags_dedupes_and_drops_category():
    raw = ["Postgres", "postgres", "POSTGRES", "Programming", "fastapi", "FastAPI"]
    out = canonicalize_tags(raw, drop_equal_to=["Programming"], max_count=10)
    assert out == ["postgres", "fastapi"]
def test_canonicalize_tags_caps_count():
    raw = [f"topic-{i}" for i in range(50)]
    out = canonicalize_tags(raw, max_count=15)
    assert len(out) == 15
    assert out[0] == "topic-0"