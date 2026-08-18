"""Tests for AirVault types, especially SensitivityTier."""

from airvault.types import SensitivityTier


class TestSensitivityTier:
    def test_allowed_tiers_public(self):
        assert SensitivityTier.PUBLIC.allowed_tiers() == ["public"]

    def test_allowed_tiers_internal(self):
        assert SensitivityTier.INTERNAL.allowed_tiers() == ["public", "internal"]

    def test_allowed_tiers_confidential(self):
        assert SensitivityTier.CONFIDENTIAL.allowed_tiers() == ["public", "internal", "confidential"]

    def test_allowed_tiers_restricted(self):
        assert SensitivityTier.RESTRICTED.allowed_tiers() == [
            "public", "internal", "confidential", "restricted"
        ]

    def test_tier_ordering(self):
        assert SensitivityTier.RESTRICTED > SensitivityTier.PUBLIC
        assert SensitivityTier.CONFIDENTIAL > SensitivityTier.INTERNAL
        assert SensitivityTier.PUBLIC >= SensitivityTier.PUBLIC
        assert not SensitivityTier.PUBLIC > SensitivityTier.INTERNAL

    def test_string_construction(self):
        assert SensitivityTier("public") == SensitivityTier.PUBLIC
        assert SensitivityTier("restricted") == SensitivityTier.RESTRICTED
