"""
Owner enrichment — looks up homeowner names from property/assessor records.

This is a stub.  The real implementation will call a paid property-records API
(e.g. ATTOM, BatchData, Estated) once a service is chosen.  Failures are
non-fatal: log a warning and return the listing unchanged.
"""
from __future__ import annotations

import logging

from src.models import Listing

logger = logging.getLogger(__name__)


def enrich_owners(listings: list[Listing], api_key: str) -> list[Listing]:
    """Attempt to fill `homeowner_name` on each listing.

    Returns the same list with homeowner_name set where available.
    Any per-listing failure is logged as a warning; the run continues.
    """
    logger.warning(
        "Owner enrichment is not yet implemented — "
        "homeowner_name will be None for all %d listing(s).",
        len(listings),
    )
    return listings
