from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.models import Listing

_DEFAULT_PATH = Path(__file__).parent.parent / "state" / "seen_listings.json"
_MAX_IDS = 50_000


@dataclass
class State:
    last_run_utc: datetime
    listing_ids: list[str] = field(default_factory=list)

    def fetch_since(self) -> datetime:
        """Fetch window start: last run minus 1 day for safety overlap."""
        return self.last_run_utc - timedelta(days=1)


def load_state(path: Path = _DEFAULT_PATH) -> State:
    with open(path) as f:
        data = json.load(f)
    last_run = datetime.fromisoformat(data["last_run_utc"])
    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=timezone.utc)
    return State(last_run_utc=last_run, listing_ids=data.get("listing_ids", []))


def save_state(state: State, path: Path = _DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_run_utc": state.last_run_utc.isoformat(),
        "listing_ids": state.listing_ids,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def filter_new(listings: list[Listing], state: State) -> list[Listing]:
    """Return only listings whose listing_id has not been seen before."""
    seen = set(state.listing_ids)
    return [l for l in listings if l.listing_id not in seen]


def add_listings(
    state: State, listings: list[Listing], run_time: datetime
) -> None:
    """
    Append unseen listing IDs to state, cap total at _MAX_IDS (most recent
    retained), and update last_run_utc.  Mutates state in place.
    """
    seen = set(state.listing_ids)
    for listing in listings:
        if listing.listing_id not in seen:
            state.listing_ids.append(listing.listing_id)
            seen.add(listing.listing_id)
    if len(state.listing_ids) > _MAX_IDS:
        state.listing_ids = state.listing_ids[-_MAX_IDS:]
    state.last_run_utc = run_time
