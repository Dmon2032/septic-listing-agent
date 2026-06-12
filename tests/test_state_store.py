from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.models import Listing
from src.state_store import State, add_listings, filter_new, load_state, save_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc


def make_listing(listing_id: str) -> Listing:
    return Listing(
        listing_id=listing_id, mls_number=None,
        list_date=date(2026, 1, 1), list_price=None,
        address_line="1 Test St", city="Testville", state="CA", zip_code="92024",
        beds=None, baths=None, sqft=None,
        listing_url=None, agent_name=None, agent_phone=None, agent_email=None,
    )


def write_state_file(path: Path, last_run: str, ids: list[str]) -> None:
    path.write_text(json.dumps({"last_run_utc": last_run, "listing_ids": ids}))


# ---------------------------------------------------------------------------
# load_state
# ---------------------------------------------------------------------------

def test_load_parses_utc_z_suffix(tmp_path: Path) -> None:
    """Datetime with 'Z' suffix (standard UTC notation) must be parsed correctly."""
    f = tmp_path / "state.json"
    write_state_file(f, "2026-05-18T13:00:00Z", ["A001", "A002"])
    state = load_state(f)
    assert state.last_run_utc == datetime(2026, 5, 18, 13, 0, 0, tzinfo=UTC)
    assert state.listing_ids == ["A001", "A002"]


def test_load_parses_offset_suffix(tmp_path: Path) -> None:
    """+00:00 suffix (written by save_state) must also load correctly."""
    f = tmp_path / "state.json"
    write_state_file(f, "2026-05-18T13:00:00+00:00", ["B001"])
    state = load_state(f)
    assert state.last_run_utc.tzinfo is not None
    assert state.listing_ids == ["B001"]


def test_load_empty_ids(tmp_path: Path) -> None:
    f = tmp_path / "state.json"
    write_state_file(f, "1970-01-01T00:00:00Z", [])
    state = load_state(f)
    assert state.listing_ids == []


# ---------------------------------------------------------------------------
# save_state / round-trip
# ---------------------------------------------------------------------------

def test_save_creates_file(tmp_path: Path) -> None:
    f = tmp_path / "sub" / "state.json"
    state = State(
        last_run_utc=datetime(2026, 6, 1, 6, 0, 0, tzinfo=UTC),
        listing_ids=["X001"],
    )
    save_state(state, f)
    assert f.exists()
    data = json.loads(f.read_text())
    assert data["listing_ids"] == ["X001"]


def test_round_trip(tmp_path: Path) -> None:
    f = tmp_path / "state.json"
    original = State(
        last_run_utc=datetime(2026, 6, 12, 13, 0, 0, tzinfo=UTC),
        listing_ids=["R001", "R002", "R003"],
    )
    save_state(original, f)
    loaded = load_state(f)
    assert loaded.last_run_utc == original.last_run_utc
    assert loaded.listing_ids == original.listing_ids


# ---------------------------------------------------------------------------
# filter_new
# ---------------------------------------------------------------------------

def test_filter_new_removes_seen_ids() -> None:
    state = State(
        last_run_utc=datetime(2026, 1, 1, tzinfo=UTC),
        listing_ids=["OLD001", "OLD002"],
    )
    listings = [make_listing("OLD001"), make_listing("NEW001"), make_listing("NEW002")]
    result = filter_new(listings, state)
    assert [l.listing_id for l in result] == ["NEW001", "NEW002"]


def test_filter_new_empty_state_returns_all() -> None:
    state = State(last_run_utc=datetime(2026, 1, 1, tzinfo=UTC), listing_ids=[])
    listings = [make_listing("A"), make_listing("B")]
    assert filter_new(listings, state) == listings


def test_filter_new_all_seen_returns_empty() -> None:
    state = State(
        last_run_utc=datetime(2026, 1, 1, tzinfo=UTC),
        listing_ids=["A", "B"],
    )
    assert filter_new([make_listing("A"), make_listing("B")], state) == []


# ---------------------------------------------------------------------------
# add_listings
# ---------------------------------------------------------------------------

def test_add_listings_appends_new_ids() -> None:
    state = State(last_run_utc=datetime(2026, 1, 1, tzinfo=UTC), listing_ids=[])
    run_time = datetime(2026, 6, 12, 13, 0, 0, tzinfo=UTC)
    add_listings(state, [make_listing("N001"), make_listing("N002")], run_time)
    assert "N001" in state.listing_ids
    assert "N002" in state.listing_ids


def test_add_listings_updates_run_time() -> None:
    run_time = datetime(2026, 6, 12, 13, 0, 0, tzinfo=UTC)
    state = State(last_run_utc=datetime(2026, 1, 1, tzinfo=UTC), listing_ids=[])
    add_listings(state, [make_listing("X")], run_time)
    assert state.last_run_utc == run_time


def test_add_listings_no_duplicates() -> None:
    state = State(
        last_run_utc=datetime(2026, 1, 1, tzinfo=UTC),
        listing_ids=["EXISTING"],
    )
    run_time = datetime(2026, 6, 12, tzinfo=UTC)
    add_listings(state, [make_listing("EXISTING"), make_listing("NEW")], run_time)
    assert state.listing_ids.count("EXISTING") == 1
    assert "NEW" in state.listing_ids


def test_add_listings_caps_at_50000() -> None:
    state = State(
        last_run_utc=datetime(2026, 1, 1, tzinfo=UTC),
        listing_ids=[f"OLD{i:05d}" for i in range(50_000)],
    )
    run_time = datetime(2026, 6, 12, tzinfo=UTC)
    new_listings = [make_listing(f"NEW{i:03d}") for i in range(10)]
    add_listings(state, new_listings, run_time)
    assert len(state.listing_ids) == 50_000
    # Most-recent entries are kept
    for i in range(10):
        assert f"NEW{i:03d}" in state.listing_ids
    # Oldest entries were dropped
    assert "OLD00000" not in state.listing_ids


def test_add_listings_empty_input_still_updates_run_time() -> None:
    old_time = datetime(2026, 1, 1, tzinfo=UTC)
    run_time = datetime(2026, 6, 12, tzinfo=UTC)
    state = State(last_run_utc=old_time, listing_ids=["A"])
    add_listings(state, [], run_time)
    assert state.last_run_utc == run_time
    assert state.listing_ids == ["A"]


# ---------------------------------------------------------------------------
# fetch_since
# ---------------------------------------------------------------------------

def test_fetch_since_is_one_day_before_last_run() -> None:
    last_run = datetime(2026, 6, 9, 6, 0, 0, tzinfo=UTC)
    state = State(last_run_utc=last_run, listing_ids=[])
    assert state.fetch_since() == last_run - timedelta(days=1)
