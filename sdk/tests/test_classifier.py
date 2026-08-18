"""Tests for sensitivity classifier."""

from airvault.ingestion.classifier import SensitivityClassifier
from airvault.types import SensitivityTier


class TestSensitivityClassifier:
    def setup_method(self):
        self.classifier = SensitivityClassifier()

    def test_public_by_default(self):
        assert self.classifier.classify("Normal meeting notes about quarterly goals.") == SensitivityTier.PUBLIC

    def test_restricted_keywords(self):
        assert self.classifier.classify("This is a CLASSIFIED document.") == SensitivityTier.RESTRICTED
        assert self.classifier.classify("TOP SECRET material") == SensitivityTier.RESTRICTED
        assert self.classifier.classify("EYES ONLY briefing") == SensitivityTier.RESTRICTED

    def test_confidential_keywords(self):
        assert self.classifier.classify("CONFIDENTIAL: merger details") == SensitivityTier.CONFIDENTIAL
        assert self.classifier.classify("This is proprietary technology.") == SensitivityTier.CONFIDENTIAL
        assert self.classifier.classify("Non-disclosure agreement terms") == SensitivityTier.CONFIDENTIAL

    def test_internal_keywords(self):
        assert self.classifier.classify("Internal only: HR policy update.") == SensitivityTier.INTERNAL
        assert self.classifier.classify("DRAFT - not for distribution") == SensitivityTier.INTERNAL
        assert self.classifier.classify("Do not distribute outside the company.") == SensitivityTier.INTERNAL

    def test_case_insensitive(self):
        assert self.classifier.classify("classified report") == SensitivityTier.RESTRICTED
        assert self.classifier.classify("CLASSIFIED REPORT") == SensitivityTier.RESTRICTED

    def test_highest_tier_wins(self):
        text = "This is both confidential and CLASSIFIED material."
        assert self.classifier.classify(text) == SensitivityTier.RESTRICTED

    def test_classify_with_evidence(self):
        tier, evidence = self.classifier.classify_with_evidence("Top secret document")
        assert tier == SensitivityTier.RESTRICTED
        assert len(evidence) > 0

    def test_no_evidence_for_public(self):
        tier, evidence = self.classifier.classify_with_evidence("Normal quarterly report")
        assert tier == SensitivityTier.PUBLIC
        assert evidence == []
