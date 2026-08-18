"""Tests for the sensitivity classifier."""

import pytest
from app.classifier import SensitivityClassifier
from app.models import SensitivityTier


class TestSensitivityClassifier:
    def setup_method(self):
        self.classifier = SensitivityClassifier()

    def test_restricted_keyword(self):
        text = "This document is CLASSIFIED and for official use only."
        assert self.classifier.classify(text) == SensitivityTier.RESTRICTED

    def test_top_secret(self):
        text = "TOP SECRET information contained within."
        assert self.classifier.classify(text) == SensitivityTier.RESTRICTED

    def test_confidential_keyword(self):
        text = "This is a confidential memo regarding the merger."
        assert self.classifier.classify(text) == SensitivityTier.CONFIDENTIAL

    def test_proprietary(self):
        text = "PROPRIETARY — do not share outside the organization."
        assert self.classifier.classify(text) == SensitivityTier.CONFIDENTIAL

    def test_internal_only(self):
        text = "This document is for internal only distribution."
        assert self.classifier.classify(text) == SensitivityTier.INTERNAL

    def test_do_not_distribute(self):
        text = "Please do not distribute this draft."
        assert self.classifier.classify(text) == SensitivityTier.INTERNAL

    def test_public_by_default(self):
        text = "Welcome to our company. Here is our public FAQ."
        assert self.classifier.classify(text) == SensitivityTier.PUBLIC

    def test_empty_text_is_public(self):
        assert self.classifier.classify("") == SensitivityTier.PUBLIC

    def test_highest_tier_wins(self):
        """If both RESTRICTED and CONFIDENTIAL patterns match, RESTRICTED wins."""
        text = "This CLASSIFIED confidential document is restricted."
        assert self.classifier.classify(text) == SensitivityTier.RESTRICTED

    def test_case_insensitive(self):
        text = "this is a Confidential document."
        assert self.classifier.classify(text) == SensitivityTier.CONFIDENTIAL
