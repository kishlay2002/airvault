"""Tests for compliance-aware retrieval filtering.

These tests verify that the access control layer at the retrieval boundary
works correctly — the core differentiator of VaultMind.
"""

import pytest
from app.models.common import SensitivityTier
from app.services.retrieval import build_access_filter


class TestBuildAccessFilter:
    """Test that access filters correctly scope allowed tiers."""

    def test_public_user_sees_only_public(self):
        f = build_access_filter(SensitivityTier.PUBLIC)
        conditions = f.must
        assert len(conditions) == 1
        allowed = conditions[0].match.any
        assert allowed == ["public"]

    def test_internal_user_sees_public_and_internal(self):
        f = build_access_filter(SensitivityTier.INTERNAL)
        allowed = f.must[0].match.any
        assert allowed == ["public", "internal"]

    def test_confidential_user_sees_three_tiers(self):
        f = build_access_filter(SensitivityTier.CONFIDENTIAL)
        allowed = f.must[0].match.any
        assert allowed == ["public", "internal", "confidential"]

    def test_restricted_user_sees_all_tiers(self):
        f = build_access_filter(SensitivityTier.RESTRICTED)
        allowed = f.must[0].match.any
        assert allowed == ["public", "internal", "confidential", "restricted"]


class TestSensitivityTierAllowed:
    """Test the SensitivityTier.allowed_tiers() helper."""

    def test_public_allowed(self):
        assert SensitivityTier.PUBLIC.allowed_tiers() == ["public"]

    def test_internal_allowed(self):
        assert SensitivityTier.INTERNAL.allowed_tiers() == ["public", "internal"]

    def test_confidential_allowed(self):
        assert SensitivityTier.CONFIDENTIAL.allowed_tiers() == [
            "public", "internal", "confidential"
        ]

    def test_restricted_allowed(self):
        assert SensitivityTier.RESTRICTED.allowed_tiers() == [
            "public", "internal", "confidential", "restricted"
        ]
