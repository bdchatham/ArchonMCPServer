"""ARN format validation for the archon.resolve tool."""

from ..models import ARNValidationResult

_ARN_PREFIX = "arn:archon:"
_VALID_TYPES = frozenset({"code", "doc", "k8s", "infra"})


def validate_arn(arn: str) -> ARNValidationResult:
    """Validate ARN format without resolving.

    Expected format::

        arn:archon:<type>:<workspace>/<package>/<path>[#<symbol>]

    Args:
        arn: ARN string to validate.

    Returns:
        ARNValidationResult with ``valid`` flag and optional ``error`` message.
    """
    if not arn:
        return ARNValidationResult(valid=False, error="ARN cannot be empty")

    if not arn.startswith(_ARN_PREFIX):
        return ARNValidationResult(
            valid=False,
            error="ARN must start with 'arn:archon:'",
        )

    remainder = arn[len(_ARN_PREFIX):]

    type_and_resource = remainder.split(":", 1)
    if len(type_and_resource) != 2 or not type_and_resource[1]:
        return ARNValidationResult(
            valid=False,
            error="ARN must have type and resource components separated by ':'",
        )

    arn_type, resource = type_and_resource

    if arn_type not in _VALID_TYPES:
        valid_list = ", ".join(sorted(_VALID_TYPES))
        return ARNValidationResult(
            valid=False,
            error=f"Invalid ARN type '{arn_type}'. Must be one of: {valid_list}",
        )

    resource_path = resource.split("#", 1)[0]
    segments = resource_path.split("/")
    if len(segments) < 3:
        return ARNValidationResult(
            valid=False,
            error="ARN resource must contain workspace/package/path",
        )

    if any(not segment for segment in segments[:3]):
        return ARNValidationResult(
            valid=False,
            error="ARN resource segments (workspace, package, path) cannot be empty",
        )

    return ARNValidationResult(valid=True)
