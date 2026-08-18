import re
import structlog

from app.models import SensitivityTier

logger = structlog.get_logger()

# Keyword patterns for sensitivity classification (case-insensitive)
SENSITIVITY_PATTERNS: dict[SensitivityTier, list[str]] = {
    SensitivityTier.RESTRICTED: [
        r"\brestricted\b",
        r"\btop\s*secret\b",
        r"\bclassified\b",
        r"\bsecret\b",
        r"\bfor\s+official\s+use\s+only\b",
        r"\bnoforn\b",
    ],
    SensitivityTier.CONFIDENTIAL: [
        r"\bconfidential\b",
        r"\bproprietary\b",
        r"\btrade\s+secret\b",
        r"\bnon[\-\s]?disclosure\b",
        r"\bnda\b",
        r"\bprivate\s+and\s+confidential\b",
    ],
    SensitivityTier.INTERNAL: [
        r"\binternal\s+only\b",
        r"\binternal\s+use\b",
        r"\bdo\s+not\s+distribute\b",
        r"\bnot\s+for\s+external\b",
        r"\bemployee\s+only\b",
        r"\bdraft\b",
    ],
}


class SensitivityClassifier:
    """Rule-based sensitivity classifier for documents.

    Uses keyword pattern matching against the first N characters of a document.
    Designed to be auditable and explainable — every classification decision
    can be traced to a specific pattern match.
    """

    def __init__(self, scan_chars: int = 5000):
        self.scan_chars = scan_chars
        self._compiled: dict[SensitivityTier, list[re.Pattern]] = {
            tier: [re.compile(p, re.IGNORECASE) for p in patterns]
            for tier, patterns in SENSITIVITY_PATTERNS.items()
        }

    def classify(self, text: str) -> SensitivityTier:
        """Classify document text into a sensitivity tier.

        Scans the first `scan_chars` characters for keyword patterns.
        Returns the highest matching tier, or PUBLIC if no patterns match.
        """
        scan_text = text[: self.scan_chars]

        # Check from highest to lowest sensitivity
        for tier in [
            SensitivityTier.RESTRICTED,
            SensitivityTier.CONFIDENTIAL,
            SensitivityTier.INTERNAL,
        ]:
            for pattern in self._compiled[tier]:
                match = pattern.search(scan_text)
                if match:
                    logger.info(
                        "sensitivity_classified",
                        tier=tier.value,
                        matched_pattern=pattern.pattern,
                        matched_text=match.group(),
                    )
                    return tier

        logger.info("sensitivity_classified", tier="public", matched_pattern=None)
        return SensitivityTier.PUBLIC
