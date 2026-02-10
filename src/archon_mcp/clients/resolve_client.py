"""Client for ARN resolution via the Code Graph GraphQL API."""

from __future__ import annotations

import httpx

from ..models import ResolveResult
from .exceptions import ServiceUnavailableError

_GRAPHQL_PATH = "/graphql"

_RESOLVE_QUERY = """
query ResolveARN($arn: ID!) {
  node(arn: $arn) {
    file_path
    line_number
  }
}
"""


class ResolveClient:
    """Async client that resolves ARNs to file locations via the Code Graph.

    Usage::

        async with ResolveClient(base_url="http://graph:8080") as client:
            result = await client.resolve("arn:archon:code:ws/pkg/path#sym")
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> ResolveClient:
        self._client = httpx.AsyncClient(base_url=self.base_url)
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def resolve(self, arn: str, timeout: float = 10.0) -> ResolveResult:
        """Resolve an ARN to its file location.

        Args:
            arn: A validated ARN string.
            timeout: Request timeout in seconds.

        Returns:
            ResolveResult indicating whether the resource was found and its location.

        Raises:
            ServiceUnavailableError: When the Code Graph service is unreachable.
        """
        if self._client is None:
            raise RuntimeError("ResolveClient must be used as an async context manager")

        try:
            response = await self._client.post(
                _GRAPHQL_PATH,
                json={"query": _RESOLVE_QUERY, "variables": {"arn": arn}},
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
        node = (body.get("data") or {}).get("node")

        if node is None:
            return ResolveResult(found=False)

        return ResolveResult(
            found=True,
            file_path=node.get("file_path"),
            line_number=node.get("line_number"),
        )
