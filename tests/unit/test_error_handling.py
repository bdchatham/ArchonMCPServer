"""Unit tests for custom exception classes."""

from archon_mcp.clients.exceptions import (
    GraphQLValidationError,
    ServiceUnavailableError,
)


class TestServiceUnavailableError:
    """Verify ServiceUnavailableError carries structured context."""

    def test_attributes(self) -> None:
        exc = ServiceUnavailableError(service_name="Code Graph", details="Connection refused")
        assert exc.service_name == "Code Graph"
        assert exc.details == "Connection refused"

    def test_message_format(self) -> None:
        exc = ServiceUnavailableError(service_name="Vector Store", details="timeout")
        assert str(exc) == "Vector Store unavailable: timeout"

    def test_is_exception(self) -> None:
        exc = ServiceUnavailableError(service_name="svc", details="err")
        assert isinstance(exc, Exception)


class TestGraphQLValidationError:
    """Verify GraphQLValidationError carries the validation message."""

    def test_message_attribute(self) -> None:
        exc = GraphQLValidationError(message="Syntax error at line 1")
        assert exc.message == "Syntax error at line 1"

    def test_str_representation(self) -> None:
        exc = GraphQLValidationError(message="Cannot query field 'x'")
        assert str(exc) == "Cannot query field 'x'"

    def test_is_exception(self) -> None:
        exc = GraphQLValidationError(message="err")
        assert isinstance(exc, Exception)
