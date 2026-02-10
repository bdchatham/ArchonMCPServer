"""Unit tests for enhanced tool response models."""

from dataclasses import asdict

from archon_mcp.models import (
    ARNValidationResult,
    EnhancedSearchResult,
    GraphQLError,
    GraphQueryOutput,
    ResolveOutput,
    ResolveResult,
)


class TestEnhancedSearchResult:
    """Verify EnhancedSearchResult construction, defaults, and serialization."""

    def test_construction_with_required_fields(self) -> None:
        result = EnhancedSearchResult(
            content="def hello(): ...",
            source="ArchonAgent/src/main.py",
            score=0.95,
            chunk_index=0,
            repo="ArchonAgent",
            arn="arn:archon:code:ws/ArchonAgent/src/main.py#hello",
        )
        assert result.content == "def hello(): ..."
        assert result.source == "ArchonAgent/src/main.py"
        assert result.score == 0.95
        assert result.chunk_index == 0
        assert result.repo == "ArchonAgent"
        assert result.arn == "arn:archon:code:ws/ArchonAgent/src/main.py#hello"

    def test_default_values_for_optional_fields(self) -> None:
        result = EnhancedSearchResult(
            content="text",
            source="src/lib.py",
            score=0.5,
            chunk_index=1,
            repo="Repo",
            arn="arn:archon:code:ws/Repo/src/lib.py",
        )
        assert result.related_arns == []
        assert result.symbol_name is None
        assert result.symbol_kind is None
        assert result.package == ""

    def test_construction_with_all_fields(self) -> None:
        result = EnhancedSearchResult(
            content="class Foo: ...",
            source="pkg/foo.py",
            score=0.88,
            chunk_index=2,
            repo="MyRepo",
            arn="arn:archon:code:ws/MyRepo/pkg/foo.py#Foo",
            related_arns=[
                "arn:archon:code:ws/MyRepo/pkg/bar.py#Bar",
                "arn:archon:code:ws/MyRepo/pkg/baz.py#Baz",
            ],
            symbol_name="Foo",
            symbol_kind="class",
            package="MyRepo",
        )
        assert result.symbol_name == "Foo"
        assert result.symbol_kind == "class"
        assert result.package == "MyRepo"
        assert len(result.related_arns) == 2

    def test_backward_compatible_fields_present_in_serialization(self) -> None:
        result = EnhancedSearchResult(
            content="x",
            source="s",
            score=0.1,
            chunk_index=0,
            repo="r",
            arn="arn:archon:code:ws/r/s",
        )
        data = asdict(result)
        for field_name in ("content", "source", "score", "chunk_index", "repo"):
            assert field_name in data

    def test_arn_metadata_fields_present_in_serialization(self) -> None:
        result = EnhancedSearchResult(
            content="x",
            source="s",
            score=0.1,
            chunk_index=0,
            repo="r",
            arn="arn:archon:code:ws/r/s",
        )
        data = asdict(result)
        for field_name in ("arn", "related_arns", "symbol_name", "symbol_kind", "package"):
            assert field_name in data


class TestGraphQueryOutput:
    """Verify GraphQueryOutput construction with data and/or errors."""

    def test_construction_with_data_only(self) -> None:
        output = GraphQueryOutput(data={"node": {"arn": "arn:archon:code:ws/pkg/f.py"}})
        assert output.data == {"node": {"arn": "arn:archon:code:ws/pkg/f.py"}}
        assert output.errors is None

    def test_construction_with_errors_only(self) -> None:
        error = GraphQLError(message="Field 'bad' not found")
        output = GraphQueryOutput(data=None, errors=[error])
        assert output.data is None
        assert len(output.errors) == 1
        assert output.errors[0].message == "Field 'bad' not found"

    def test_construction_with_data_and_errors(self) -> None:
        error = GraphQLError(message="Partial failure")
        output = GraphQueryOutput(
            data={"partial": "result"},
            errors=[error],
        )
        assert output.data == {"partial": "result"}
        assert output.errors is not None
        assert len(output.errors) == 1

    def test_graphql_error_with_all_optional_fields(self) -> None:
        error = GraphQLError(
            message="Syntax error",
            locations=[{"line": 1, "column": 5}],
            path=["node", 0, "arn"],
            extensions={"code": "GRAPHQL_VALIDATION_FAILED"},
        )
        assert error.message == "Syntax error"
        assert error.locations == [{"line": 1, "column": 5}]
        assert error.path == ["node", 0, "arn"]
        assert error.extensions == {"code": "GRAPHQL_VALIDATION_FAILED"}

    def test_graphql_error_defaults(self) -> None:
        error = GraphQLError(message="Something went wrong")
        assert error.locations is None
        assert error.path is None
        assert error.extensions is None

    def test_serialization_preserves_structure(self) -> None:
        error = GraphQLError(message="err")
        output = GraphQueryOutput(data={"key": "val"}, errors=[error])
        data = asdict(output)
        assert data["data"] == {"key": "val"}
        assert len(data["errors"]) == 1
        assert data["errors"][0]["message"] == "err"


class TestResolveOutput:
    """Verify ResolveOutput construction for success and failure cases."""

    def test_success_with_file_path_and_line_number(self) -> None:
        output = ResolveOutput(success=True, file_path="src/main.py", line_number=42)
        assert output.success is True
        assert output.file_path == "src/main.py"
        assert output.line_number == 42
        assert output.error is None

    def test_success_without_line_number(self) -> None:
        output = ResolveOutput(success=True, file_path="docs/readme.md")
        assert output.success is True
        assert output.file_path == "docs/readme.md"
        assert output.line_number is None
        assert output.error is None

    def test_failure_with_error_message(self) -> None:
        output = ResolveOutput(success=False, error="Resource not found for ARN")
        assert output.success is False
        assert output.error == "Resource not found for ARN"
        assert output.file_path is None
        assert output.line_number is None

    def test_failure_no_file_path_or_line_number(self) -> None:
        output = ResolveOutput(success=False, error="Invalid ARN format")
        assert output.file_path is None
        assert output.line_number is None


class TestResolveResult:
    """Verify ResolveResult construction for found and not-found cases."""

    def test_found_with_file_path_and_line_number(self) -> None:
        result = ResolveResult(found=True, file_path="src/handler.py", line_number=10)
        assert result.found is True
        assert result.file_path == "src/handler.py"
        assert result.line_number == 10

    def test_not_found(self) -> None:
        result = ResolveResult(found=False)
        assert result.found is False
        assert result.file_path is None
        assert result.line_number is None
