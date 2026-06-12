from __future__ import annotations

from datetime import date

import pytest

from src.config import Keywords
from src.filters.septic import is_septic
from src.models import Listing

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

KEYWORDS = Keywords(
    structured_sewer_values=["septic", "septic tank", "private", "owts", "on-site", "cesspool"],
    description_keywords=["septic", "septic system", "owts", "on-site wastewater"],
    negation_patterns=[
        "no septic", "not on septic", "removed septic",
        "converted to sewer", "sewer connected", "public sewer", "city sewer",
    ],
)


def listing(*, sewer: list[str] | None = None, remarks: str = "") -> Listing:
    return Listing(
        listing_id="T001", mls_number=None,
        list_date=date(2026, 1, 1), list_price=None,
        address_line="1 Test St", city="Testville", state="CA", zip_code="92024",
        beds=None, baths=None, sqft=None,
        sewer=sewer or [],
        public_remarks=remarks,
        listing_url=None,
        agent_name=None, agent_phone=None, agent_email=None,
    )


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------

def test_structured_septic_tank():
    """Sewer field = ['Septic Tank'] → match via structured field."""
    matched, reason, snippet = is_septic(listing(sewer=["Septic Tank"]), KEYWORDS)
    assert matched is True
    assert reason.startswith("structured:")
    assert snippet is None  # structured matches never carry a snippet


def test_description_septic_system():
    """Description contains 'on septic system' → description match."""
    matched, reason, snippet = is_septic(
        listing(remarks="Property is on septic system."), KEYWORDS
    )
    assert matched is True
    assert reason.startswith("description:")
    assert snippet is not None
    assert "septic" in snippet.lower()


def test_description_owts():
    """Description contains 'OWTS' → description match."""
    matched, reason, snippet = is_septic(
        listing(remarks="OWTS permit on file."), KEYWORDS
    )
    assert matched is True
    assert "owts" in reason.lower()
    assert snippet is not None


def test_description_on_site_wastewater_mixed_case():
    """'On-Site Wastewater' with mixed case → description match (case-insensitive)."""
    matched, reason, snippet = is_septic(
        listing(remarks="On-Site Wastewater system installed 2019."), KEYWORDS
    )
    assert matched is True
    assert snippet is not None


def test_both_structured_and_description_match():
    """Both structured + description match → single match, structured reason, no snippet."""
    matched, reason, snippet = is_septic(
        listing(sewer=["Septic Tank"], remarks="Septic recently pumped and inspected."),
        KEYWORDS,
    )
    assert matched is True
    assert reason.startswith("structured:")  # structured checked first
    assert snippet is None                  # no double-count, snippet only from description


# ---------------------------------------------------------------------------
# Negative cases
# ---------------------------------------------------------------------------

def test_public_sewer_no_match():
    """Sewer field = ['Public Sewer'], no description keywords → no match."""
    matched, reason, snippet = is_septic(listing(sewer=["Public Sewer"]), KEYWORDS)
    assert matched is False
    assert snippet is None


def test_negation_no_septic_public_sewer():
    """'No septic — public sewer connected.' → negation guard fires."""
    matched, reason, snippet = is_septic(
        listing(remarks="No septic — public sewer connected."), KEYWORDS
    )
    assert matched is False
    assert reason.startswith("negated:")


def test_negation_septic_removed_city_sewer():
    """'Septic was removed; now on city sewer.' → negation guard fires ('city sewer')."""
    matched, reason, snippet = is_septic(
        listing(remarks="Septic was removed; now on city sewer."), KEYWORDS
    )
    assert matched is False
    assert reason.startswith("negated:")


def test_false_positive_septic_style():
    """
    'septic-style fermentation' triggers a word-boundary match and is flagged as
    matched=True — this is a documented acceptable false positive.  The hyphen after
    'septic' is a non-word character, so \\bseptic\\b matches.  Real-estate context
    makes this occurrence essentially impossible; we do not add special logic to
    suppress it.
    """
    matched, reason, snippet = is_septic(
        listing(remarks="Natural wines made with septic-style fermentation."), KEYWORDS
    )
    assert matched is True  # expected false positive — see docstring


def test_empty_fields_no_crash():
    """Empty sewer list and empty remarks → no match, no exception."""
    matched, reason, snippet = is_septic(listing(sewer=[], remarks=""), KEYWORDS)
    assert matched is False
    assert snippet is None


# ---------------------------------------------------------------------------
# Snippet bounds
# ---------------------------------------------------------------------------

def test_snippet_is_bounded():
    """Snippet must be ≤ 120 chars (±60 around the keyword)."""
    long_prefix = "x" * 200
    long_suffix = "y" * 200
    remarks = f"{long_prefix} septic system {long_suffix}"
    matched, reason, snippet = is_septic(listing(remarks=remarks), KEYWORDS)
    assert matched is True
    assert snippet is not None
    assert len(snippet) <= 120 + len("septic system")  # keyword itself can push past 120


def test_snippet_contains_keyword():
    """Snippet always contains the matched keyword."""
    matched, reason, snippet = is_septic(
        listing(remarks="Great home, septic system in excellent condition."), KEYWORDS
    )
    assert matched is True
    assert snippet is not None
    assert "septic" in snippet.lower()
