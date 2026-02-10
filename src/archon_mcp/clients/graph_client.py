"""GraphQL client for the Code Graph service."""

from __future__ import annotations

import httpx

from ..models import GraphQueryOutput, GraphQLError
from .exceptions import GraphQLValidationError, ServiceUnavailableError

_GRAPHQL_PATH = "/graphql"


class GraphClient:
    """Async client for executing GraphQL queries against the Code Graph.

    Usage::

        async with GraphClient(base_url="http://graph:8080") as client:
            result = await client.execute("{ node(arn: \"...\") { arn kind } }")
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> GraphClient:
        self._client = httpx.AsyncClient(base_url=self.base_url)
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def execute(
        self,
        query: str,
        variables: dict | None = None,
        timeout: float = 30.0,
    ) -> GraphQueryOutput:
        """Execute a GraphQL query against the Code Graph.

        Args:
            query: GraphQL query string.
            variables: Optional mapping of query variables.
            timeout: Request timeout in seconds.

        Returns:
            GraphQueryOutput containing ``data`` and optional ``errors``.

        Raises:
            ServiceUnavailableError: When the Code Graph service is unreachable.
            GraphQLValidationError: When the query fails server-side validation.
        """
        if self._client is None:
            raise RuntimeError("GraphClient must be used as an async context manager")

        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = await self._client.post(
                _GRAPHQL_PATH,
                json=payload,
                timeout=timeout,
            )
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise ServiceUnavailableError(
                service_name="Code Graph",
                details=str(exc),
            ) from exc
        except httpx.TimeoutException as exc:
            raise ServiceUnavailableError(
                service_name="Code Graph",
                details=f"Request timed out after {timeout}s",
            ) from exc

        body = response.json()

        errors = _parse_errors(body.get("errors"))
        if errors and _is_validation_error(errors):
            raise GraphQLValidationError(message=errors[0].message)

        return GraphQueryOutput(data=body.get("data"), errors=errors or None)


def _parse_errors(raw_errors: list[dict] | None) -> list[GraphQLError] | None:
    if not raw_errors:
        return None
    return [
        GraphQLError(
            message=err.get("message", "Unknown error"),
            locations=err.get("locations"),
            path=err.get("path"),
            extensions=err.get("extensions"),
        )
        for err in raw_errors
    ]


def _is_validation_error(errors: list[GraphQLError]) -> bool:
    """Detect GraphQL validation errors from error extensions or message patterns."""
    for error in errors:
        if error.extensions and error.extensions.get("code") == "GRAPHQL_VALIDATION_FAILED":
            return True
        message_lower = error.message.lower()
        if "syntax error" in message_lower or "cannot query field" in message_lower:
            return True
    return False
