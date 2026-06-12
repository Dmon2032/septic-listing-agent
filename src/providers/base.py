from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.models import Listing


class ListingProvider(Protocol):
    def fetch_listings(
        self, zip_codes: list[str], since: datetime
    ) -> list[Listing]: ...
