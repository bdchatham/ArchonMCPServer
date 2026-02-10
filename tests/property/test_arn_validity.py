"""Property 2: ARN Metadata Validity.

For any search result with a non-null ``arn`` field, the ARN SHALL be a valid
ARN string that passes format validation.

**Validates: Requirements 1.1, 1.2**

Strategy: build valid ARN strings from components (type, workspace, package,
path, optional symbol), construct EnhancedSearchResult instances, and verify
that every non-empty ARN — both the primary ``arn`` and each entry in
``related_arns`` — passes ``validate_arn``.
"""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from archon_mcp.clients.arn_validation import validate_arn
from archon_mcp.models import EnhancedSearchResult

_VALID_TYPES = ["code", "doc", "k8s", "infra"]

_identifier = st.from_regex(r"[a-zA-Z][a-zA-Z0-9_-]{0,29}", fullmatch=True)
_file_segment = st.from_regex(r"[a-zA-Z][a-zA-Z0-9_./-]{0,39}", fullmatch=True)
_source_path = st.builds(lambda repo, path: f"{repo}/{path}", repo=_identifier, path=_identifier)


def _arn_strategy() -> st.SearchStrategy[str]:
    """Build a valid ARN from randomised components."""
    return st.builds(
        lambda arn_type, workspace, package, path, symbol: (
            f"arn:archon:{arn_type}:{workspace}/{package}/{path}"
            + (f"#{symbol}" if symbol else "")
        ),
        arn_type=st.sampled_from(_VALID_TYPES),
        workspace=_identifier,
        package=_identifier,
        path=_file_segment,
        symbol=st.one_of(st.none(), _identifier),
    )


@given(
    arn=_arn_strategy(),
    related_arns=st.lists(_arn_strategy(), min_size=0, max_size=5),
)
@settings(max_examples=100)
def test_generated_arns_pass_validation(
    arn: str,
    related_arns: list[str],
) -> None:
    """Every ARN produced by the strategy must pass format validation."""
    primary_result = validate_arn(arn)
    assert primary_result.valid, f"Primary ARN failed validation: {arn!r} — {primary_result.error}"

    for related in related_arns:
        related_result = validate_arn(related)
        assert related_result.valid, f"Related ARN failed validation: {related!r} — {related_result.error}"


@given(
    content=st.text(min_size=1, max_size=100),
    source=_source_path,
    score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    chunk_index=st.integers(min_value=0, max_value=5000),
    arn=_arn_strategy(),
    related_arns=st.lists(_arn_strategy(), min_size=0, max_size=5),
    symbol_name=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
    symbol_kind=st.one_of(st.none(), st.sampled_from(["function", "class", "method"])),
    package=_identifier,
)
@settings(max_examples=100)
def test_enhanced_search_result_arns_are_valid(
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
    """EnhancedSearchResult instances with generated ARNs must all pass validation."""
    result = EnhancedSearchResult(
        content=content,
        source=source,
        score=score,
        chunk_index=chunk_index,
        repo=source.split("/")[0],
        arn=arn,
        related_arns=related_arns,
        symbol_name=symbol_name,
        symbol_kind=symbol_kind,
        package=package,
    )

    if result.arn:
        validation = validate_arn(result.arn)
        assert validation.valid, f"Primary ARN invalid: {result.arn!r} — {validation.error}"

    for related in result.related_arns:
        validation = validate_arn(related)
        assert validation.valid, f"Related ARN invalid: {related!r} — {validation.error}"
