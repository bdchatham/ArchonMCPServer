"""Unit tests for ARN format validation."""

import pytest

from archon_mcp.clients.arn_validation import validate_arn


class TestValidArnFormats:
    """Verify that well-formed ARNs pass validation for every supported type."""

    @pytest.mark.parametrize(
        "arn",
        [
            "arn:archon:code:workspace/package/src/main.py#MyClass",
            "arn:archon:doc:workspace/package/docs/readme.md",
            "arn:archon:k8s:workspace/package/manifests/deploy.yaml",
            "arn:archon:infra:workspace/package/cdk/stack.ts",
        ],
        ids=["code", "doc", "k8s", "infra"],
    )
    def test_valid_arn_types(self, arn: str) -> None:
        result = validate_arn(arn)
        assert result.valid is True
        assert result.error is None

    def test_valid_arn_with_deep_path(self) -> None:
        result = validate_arn("arn:archon:code:ws/pkg/a/b/c/d.py#func")
        assert result.valid is True

    def test_valid_arn_without_symbol_fragment(self) -> None:
        result = validate_arn("arn:archon:code:ws/pkg/path.py")
        assert result.valid is True


class TestInvalidArnFormats:
    """Verify that malformed ARNs are rejected with descriptive errors."""

    def test_empty_string(self) -> None:
        result = validate_arn("")
        assert result.valid is False
        assert result.error == "ARN cannot be empty"

    def test_missing_prefix(self) -> None:
        result = validate_arn("not-an-arn")
        assert result.valid is False
        assert "arn:archon:" in result.error

    def test_invalid_type(self) -> None:
        result = validate_arn("arn:archon:unknown:ws/pkg/path")
        assert result.valid is False
        assert "unknown" in result.error

    def test_missing_resource(self) -> None:
        result = validate_arn("arn:archon:code:")
        assert result.valid is False

    def test_resource_without_slashes(self) -> None:
        result = validate_arn("arn:archon:code:flat-resource")
        assert result.valid is False
        assert "workspace/package/path" in result.error

    def test_resource_with_only_one_slash(self) -> None:
        result = validate_arn("arn:archon:code:workspace/package")
        assert result.valid is False
        assert "workspace/package/path" in result.error

    def test_empty_segment_in_resource(self) -> None:
        result = validate_arn("arn:archon:code:/pkg/path")
        assert result.valid is False
        assert "cannot be empty" in result.error

    def test_missing_type_and_resource(self) -> None:
        result = validate_arn("arn:archon:")
        assert result.valid is False
