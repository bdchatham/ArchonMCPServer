"""Property 1: Enhanced Search Backward Compatibility.

For any search query that succeeds, the response SHALL include all existing
fields (content, source, score, chunk_index, repo) in addition to the new
ARN metadata fields.

**Validates: Requirement 1.7**

Strategy: generate random chunk objects with varying attributes and verify
that _build_enriched_chunk always produces a dict containing every required
field — both the legacy fields and the new ARN metadata fields.
"""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from archon_mcp.server import _build_enriched_chunk

LEGACY_FIELDS = {"content", "source", "score", "chunk_index", "repo"}
ARN_METADATA_FIELDS = {"arn", "related_arns", "symbol_name", "symbol_kind", "package"}
ALL_REQUIRED_FIELDS = LEGACY_FIELDS | ARN_METADATA_FIELDS

_segment = st.from_regex(r"[a-zA-Z][a-zA-Z0-9_.-]{0,19}", fullmatch=True)
_source_path = st.builds(lambda repo, path: f"{repo}/{path}", repo=_segment, path=_segment)


class _FakeChunk:
    """Lightweight object whose attributes mirror a vector-store chunk."""

    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


@given(
    content=st.text(min_size=0, max_size=200),
    source=_source_path,
    score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    chunk_index=st.integers(min_value=0, max_value=10_000),
    arn=st.text(min_size=0, max_size=150),
    related_arns=st.lists(st.text(min_size=1, max_size=100), max_size=5),
    symbol_name=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    symbol_kind=st.one_of(st.none(), st.sampled_from(["function", "class", "method", "variable", "type", "module"])),
    package=st.text(min_size=0, max_size=50),
)
@settings(max_examples=100)
def test_enriched_chunk_contains_all_required_fields(
    content: str,
    source: str,
    score: float,
    chunk_index: int,
    arn: str,
    related_arns: list[str],
    symbol_name: str | None,
    symbol_kind: str | None,
    package: str,
) -> None:
    """Every enriched chunk dict must contain all legacy and ARN metadata fields."""
    chunk = _FakeChunk(
        content=content,
        source=source,
        score=score,
        chunk_index=chunk_index,
        arn=arn,
        related_arns=related_arns,
        symbol_name=symbol_name,
        symbol_kind=symbol_kind,
        package=package,
    )

    result = _build_enriched_chunk(chunk)

    missing = ALL_REQUIRED_FIELDS - result.keys()
    assert not missing, f"Missing fields in enriched chunk: {missing}"


@given(
    content=st.text(min_size=0, max_size=200),
    source=_source_path,
    score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    chunk_index=st.integers(min_value=0, max_value=10_000),
    arn=st.text(min_size=0, max_size=150),
    package=st.text(min_size=0, max_size=50),
)
@settings(max_examples=100)
def test_legacy_field_values_preserved(
    content: str,
    source: str,
    score: float,
    chunk_index: int,
    arn: str,
    package: str,
) -> None:
    """Legacy field values must pass through unchanged from the source chunk."""
    chunk = _FakeChunk(
        content=content,
        source=source,
        score=score,
        chunk_index=chunk_index,
        arn=arn,
        related_arns=[],
        symbol_name=None,
        symbol_kind=None,
        package=package,
    )

    result = _build_enriched_chunk(chunk)

    assert result["content"] == content
    assert result["source"] == source
    assert result["score"] == score
    assert result["chunk_index"] == chunk_index
    expected_repo = source.split("/")[0] if "/" in source else "unknown"
    assert result["repo"] == expected_repo


@given(
    content=st.text(min_size=0, max_size=100),
    source=st.text(min_size=1, max_size=50),
    score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    chunk_index=st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=100)
def test_missing_arn_metadata_defaults_gracefully(
    content: str,
    source: str,
    score: float,
    chunk_index: int,
) -> None:
    """When a chunk lacks ARN metadata attributes, defaults are applied."""
    chunk = _FakeChunk(
        content=content,
        source=source,
        score=score,
        chunk_index=chunk_index,
    )

    result = _build_enriched_chunk(chunk)

    assert ALL_REQUIRED_FIELDS <= result.keys()
    assert result["arn"] == ""
    assert result["related_arns"] == []
    assert result["symbol_name"] is None
    assert result["symbol_kind"] is None
    assert result["package"] == ""
