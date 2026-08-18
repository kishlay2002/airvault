"""Tests for compliance-aware access filter — AirVault's core differentiator."""

from airvault.retrieval.access import build_access_filter, build_redaction_filter
from airvault.types import SensitivityTier


class TestBuildAccessFilter:
    def test_public_user_sees_only_public(self):
        filt = build_access_filter(SensitivityTier.PUBLIC)
        allowed = filt.must[0].match.any
        assert allowed == ["public"]

    def test_internal_user_sees_public_and_internal(self):
        filt = build_access_filter(SensitivityTier.INTERNAL)
        allowed = filt.must[0].match.any
        assert allowed == ["public", "internal"]

    def test_confidential_user_sees_three_tiers(self):
        filt = build_access_filter(SensitivityTier.CONFIDENTIAL)
        allowed = filt.must[0].match.any
        assert allowed == ["public", "internal", "confidential"]

    def test_restricted_user_sees_all_tiers(self):
        filt = build_access_filter(SensitivityTier.RESTRICTED)
        allowed = filt.must[0].match.any
        assert allowed == ["public", "internal", "confidential", "restricted"]

    def test_filter_has_correct_field_key(self):
        filt = build_access_filter(SensitivityTier.PUBLIC)
        assert filt.must[0].key == "sensitivity_tier"

    def test_public_user_never_sees_restricted(self):
        filt = build_access_filter(SensitivityTier.PUBLIC)
        allowed = filt.must[0].match.any
        assert "restricted" not in allowed
        assert "confidential" not in allowed
        assert "internal" not in allowed

    def test_internal_user_never_sees_confidential(self):
        filt = build_access_filter(SensitivityTier.INTERNAL)
        allowed = filt.must[0].match.any
        assert "confidential" not in allowed
        assert "restricted" not in allowed


class TestBuildRedactionFilter:
    """Tests for the redaction counting filter (security fix).

    The redaction filter matches chunks ABOVE a user's clearance.
    It is used for counting only — no content is ever loaded.
    """

    def test_public_user_redaction_includes_three_tiers(self):
        filt = build_redaction_filter(SensitivityTier.PUBLIC)
        denied = filt.must[0].match.any
        assert set(denied) == {"internal", "confidential", "restricted"}

    def test_internal_user_redaction_includes_two_tiers(self):
        filt = build_redaction_filter(SensitivityTier.INTERNAL)
        denied = filt.must[0].match.any
        assert set(denied) == {"confidential", "restricted"}

    def test_confidential_user_redaction_includes_one_tier(self):
        filt = build_redaction_filter(SensitivityTier.CONFIDENTIAL)
        denied = filt.must[0].match.any
        assert set(denied) == {"restricted"}

    def test_restricted_user_has_no_redaction(self):
        filt = build_redaction_filter(SensitivityTier.RESTRICTED)
        assert filt is None

    def test_access_and_redaction_are_complementary(self):
        """Access + redaction filters must cover all 4 tiers with no overlap."""
        for tier in SensitivityTier:
            access = build_access_filter(tier)
            redaction = build_redaction_filter(tier)

            allowed = set(access.must[0].match.any)
            denied = set(redaction.must[0].match.any) if redaction else set()

            assert allowed & denied == set(), "Overlap between access and redaction"
            assert allowed | denied == {"public", "internal", "confidential", "restricted"}
