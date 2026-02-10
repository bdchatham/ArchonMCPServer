"""Property 5: ARN Validation Before Resolution.

For any call to ``archon.resolve``, the tool SHALL validate ARN format before
attempting resolution, returning a format error for malformed ARNs.

**Validates: Requirements 3.4, 3.7**

Strategy: generate a mix of valid and invalid ARN strings. For invalid ARNs,
verify the response has ``success: False`` with an error mentioning
"Invalid ARN format" and that the ResolveClient was never called.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

import archon_mcp.server as _server_mod
from archon_mcp.clients.arn_validation import validate_arn

_VALID_TYPES = ["code", "doc", "k8s", "infra"]
_identifier = st.from_regex(r"[a-zA-Z][a-zA-Z0-9_-]{0,29}", fullmatch=True)
_file_segment = st.from_regex(r"[a-zA-Z][a-zA-Z0-9_./-]{0,39}", fullmatch=True)


def _valid_arn_strategy() -> st.SearchStrategy[str]:
    """Build a syntactically valid ARN."""
    return st.builds(
        lambda arn_type, workspace, package, path: (
            f"arn:archon:{arn_type}:{workspace}/{package}/{path}"
        ),
        arn_type=st.sampled_from(_VALID_TYPES),
        workspace=_identifier,
        package=_identifier,
        path=_file_segment,
    )


def _invalid_arn_strategy() -> st.SearchStrategy[str]:
    """Generate strings that are NOT valid ARNs.

    Covers several failure modes: empty, missing prefix, bad type, and
    missing resource segments.
    """
    return st.one_of(
        st.just(""),
        st.text(min_size=1, max_size=80).filter(
            lambda s: not s.startswith("arn:archon:")
        ),
        st.builds(
            lambda bad_type: f"arn:archon:{bad_type}:ws/pkg/path",
            bad_type=st.text(min_size=1, max_size=10).filter(
                lambda t: t not in _VALID_TYPES
            ),
        ),
        st.builds(
            lambda arn_type: f"arn:archon:{arn_type}:noslash",
            arn_type=st.sampled_from(_VALID_TYPES),
        ),
        st.builds(
            lambda arn_type: f"arn:archon:{arn_type}:ws/pkg",
            arn_type=st.sampled_from(_VALID_TYPES),
        ),
    )


@pytest.mark.asyncio
@given(invalid_arn=_invalid_arn_strategy())
@settings(max_examples=100)
async def test_invalid_arn_rejected_before_resolve_client_called(
    invalid_arn: str,
) -> None:
    """Invalid ARNs must produce a format error without touching ResolveClient."""
    validation = validate_arn(invalid_arn)
    assert not validation.valid, f"Strategy produced a valid ARN: {invalid_arn!r}"

    mock_resolve_client = MagicMock()
    mock_resolve_client_instance = AsyncMock()
    mock_resolve_client.__aenter__ = AsyncMock(return_value=mock_resolve_client_instance)
    mock_resolve_client.__aexit__ = AsyncMock(return_value=False)
    mock_constructor = MagicMock(return_value=mock_resolve_client)

    with patch.object(_server_mod, "ResolveClient", mock_constructor):
        result = await _server_mod.resolve(arn=invalid_arn)

    assert result["success"] is False
    assert "Invalid ARN format" in result["error"]
    mock_constructor.assert_not_called()


@pytest.mark.asyncio
@given(valid_arn=_valid_arn_strategy())
@settings(max_examples=100)
async def test_valid_arn_reaches_resolve_client(
    valid_arn: str,
) -> None:
    """Valid ARNs must pass validation and reach the ResolveClient."""
    validation = validate_arn(valid_arn)
    assert validation.valid, f"Strategy produced an invalid ARN: {valid_arn!r}"

    mock_resolve_result = MagicMock()
    mock_resolve_result.found = True
    mock_resolve_result.file_path = "/some/path.py"
    mock_resolve_result.line_number = 42

    mock_client_instance = AsyncMock()
    mock_client_instance.resolve = AsyncMock(return_value=mock_resolve_result)

    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_context_manager.__aexit__ = AsyncMock(return_value=False)
    mock_constructor = MagicMock(return_value=mock_context_manager)

    with patch.object(_server_mod, "ResolveClient", mock_constructor):
        result = await _server_mod.resolve(arn=valid_arn)

    assert result["success"] is True
    mock_constructor.assert_called_once()
    mock_client_instance.resolve.assert_called_once_with(arn=valid_arn)
