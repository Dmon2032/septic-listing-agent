from __future__ import annotations

import logging
import re

from src.config import Keywords
from src.models import Listing

logger = logging.getLogger(__name__)


def is_septic(
    listing: Listing, keywords: Keywords
) -> tuple[bool, str, str | None]:
    """
    Returns (matched, reason, snippet).

    matched  — True if the listing appears to be on a septic/OWTS system.
    reason   — short string explaining the decision (for logging + CSV).
    snippet  — ±60-char window around the description match, or None for
               structured-field matches.

    Detection rules (spec § Septic detection):
      1. Structured: any sewer field value contains a structured_sewer_value.
      2. Description: word-boundary regex hit on description_keywords.
         Negation guard: if a negation_pattern appears within ±50 chars of
         the keyword match, the listing is excluded.
    """
    # --- 1. Structured match ---
    for sewer_val in listing.sewer:
        for pat in keywords.structured_sewer_values:
            if pat.lower() in sewer_val.lower():
                reason = f"structured:{sewer_val}"
                logger.debug("%s matched=True reason=%s", listing.listing_id, reason)
                return True, reason, None

    # --- 2. Description match ---
    text = listing.public_remarks
    for kw in keywords.description_keywords:
        rx = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        m = rx.search(text)
        if not m:
            continue

        start, end = m.start(), m.end()

        # Negation guard: ±50-char window around the matched keyword
        window = text[max(0, start - 50) : end + 50]
        for neg in keywords.negation_patterns:
            if neg.lower() in window.lower():
                reason = f"negated:{neg}"
                logger.debug(
                    "%s matched=False reason=%s", listing.listing_id, reason
                )
                return False, reason, None

        snippet = text[max(0, start - 60) : end + 60]
        reason = f"description:{kw}"
        logger.debug("%s matched=True reason=%s", listing.listing_id, reason)
        return True, reason, snippet

    logger.debug("%s matched=False reason=no_match", listing.listing_id)
    return False, "no_match", None
