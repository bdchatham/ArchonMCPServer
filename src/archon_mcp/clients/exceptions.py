"""Custom exceptions for service client error handling."""


class ServiceUnavailableError(Exception):
    """Raised when a backend service is unreachable.

    Attributes:
        service_name: Name of the unavailable service.
        details: Additional context about the failure.
    """

    def __init__(self, service_name: str, details: str) -> None:
        self.service_name = service_name
        self.details = details
        super().__init__(f"{service_name} unavailable: {details}")


class GraphQLValidationError(Exception):
    """Raised when a GraphQL query fails validation.

    Attributes:
        message: Description of the validation failure.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
