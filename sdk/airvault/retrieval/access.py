"""Compliance-aware access filter for Qdrant retrieval.

This module implements AirVault's core differentiator:
filtering at the vector DB query level so restricted chunks
are NEVER loaded into application memory for unauthorized users.
"""

from qdrant_client.models import Filter, FieldCondition, MatchAny

from airvault.types import SensitivityTier

_ALL_TIERS = ["public", "internal", "confidential", "restricted"]


def build_access_filter(user_clearance: SensitivityTier) -> Filter:
    """Build a Qdrant filter that only returns chunks at or below the user's clearance.

    Args:
        user_clearance: The caller's security clearance level.

    Returns:
        Qdrant Filter that restricts results to allowed sensitivity tiers.

    Example:
        build_access_filter(SensitivityTier.INTERNAL)
        → Filter matching chunks with sensitivity_tier IN ["public", "internal"]
    """
    allowed = user_clearance.allowed_tiers()
    return Filter(
        must=[
            FieldCondition(
                key="sensitivity_tier",
                match=MatchAny(any=allowed),
            )
        ]
    )


def build_redaction_filter(user_clearance: SensitivityTier) -> Filter | None:
    """Build a Qdrant filter matching chunks ABOVE the user's clearance.

    Used to count redacted chunks without loading their content.
    Returns None if user has RESTRICTED clearance (nothing is redacted).
    """
    allowed = set(user_clearance.allowed_tiers())
    denied = [t for t in _ALL_TIERS if t not in allowed]
    if not denied:
        return None
    return Filter(
        must=[
            FieldCondition(
                key="sensitivity_tier",
                match=MatchAny(any=denied),
            )
        ]
    )
