"""Rule-based sensitivity classifier.

Classifies text into sensitivity tiers using keyword patterns.
Rules are auditable and explainable — critical for compliance.
"""

import re

from airvault.types import SensitivityTier

TIER_PATTERNS: dict[SensitivityTier, list[str]] = {
    SensitivityTier.RESTRICTED: [
        r"\bclassified\b",
        r"\btop\s+secret\b",
        r"\beyes\s+only\b",
        r"\brestricted\b",
        r"\bsecret\b",
        r"\bnoforn\b",
    ],
    SensitivityTier.CONFIDENTIAL: [
        r"\bconfidential\b",
        r"\bproprietary\b",
        r"\btrade\s+secret\b",
        r"\bnon[\-\s]?disclosure\b",
        r"\bprivileged\b",
    ],
    SensitivityTier.INTERNAL: [
        r"\binternal\s+only\b",
        r"\bdo\s+not\s+distribute\b",
        r"\bdraft\b",
        r"\bnot\s+for\s+(public|external)\b",
        r"\bemployee\s+only\b",
    ],
}


class SensitivityClassifier:
    """Classify text sensitivity using keyword pattern matching.

    The highest-matching tier wins. If no patterns match, returns PUBLIC.
    Thread-safe and stateless.
    """

    def __init__(self, custom_patterns: dict[SensitivityTier, list[str]] | None = None):
        self.patterns = custom_patterns or TIER_PATTERNS
        self._compiled: dict[SensitivityTier, list[re.Pattern]] = {
            tier: [re.compile(p, re.IGNORECASE) for p in patterns]
            for tier, patterns in self.patterns.items()
        }

    def classify(self, text: str) -> SensitivityTier:
        """Classify text into a sensitivity tier.

        Scans the first 5000 characters for efficiency.
        Returns the highest tier matched, or PUBLIC if none.
        """
        sample = text[:5000]

        # Check tiers from highest to lowest
        tier_order = [SensitivityTier.RESTRICTED, SensitivityTier.CONFIDENTIAL, SensitivityTier.INTERNAL]

        for tier in tier_order:
            for pattern in self._compiled.get(tier, []):
                if pattern.search(sample):
                    return tier

        return SensitivityTier.PUBLIC

    def classify_with_evidence(self, text: str) -> tuple[SensitivityTier, list[str]]:
        """Classify and return matched keywords as evidence.

        Useful for audit trails and explainability.
        """
        sample = text[:5000]
        tier_order = [SensitivityTier.RESTRICTED, SensitivityTier.CONFIDENTIAL, SensitivityTier.INTERNAL]

        for tier in tier_order:
            matches = []
            for pattern in self._compiled.get(tier, []):
                found = pattern.findall(sample)
                matches.extend(found)
            if matches:
                return tier, matches

        return SensitivityTier.PUBLIC, []
