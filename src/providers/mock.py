from __future__ import annotations

from datetime import date, datetime

from src.models import Listing

# fmt: off
_LISTINGS: list[Listing] = [
    # 1 — structured match only (Septic Tank in sewer field, no description keyword)
    Listing(
        listing_id="MOCK001", mls_number="NDP2600001",
        list_date=date(2026, 6, 2), list_price=1_250_000,
        address_line="4721 Rancho Santa Fe Rd", city="Rancho Santa Fe",
        state="CA", zip_code="92067",
        beds=4, baths=3.0, sqft=2800,
        sewer=["Septic Tank"],
        public_remarks="Stunning single-story ranch on 1.5 acres. Three-car garage and pool.",
        listing_url="https://mock.example.com/MOCK001",
        agent_name="Maria Torres", agent_phone="858-555-0101",
        agent_email="mtorres@sdhomes.example.com",
    ),
    # 2 — description match only ("septic system" in remarks, no structured field)
    Listing(
        listing_id="MOCK002", mls_number="NDP2600002",
        list_date=date(2026, 6, 3), list_price=895_000,
        address_line="1840 Via Cerro", city="Encinitas",
        state="CA", zip_code="92024",
        beds=3, baths=2.0, sqft=1650,
        sewer=[],
        public_remarks="Charming cottage on a quiet street. Property is on septic system. "
                       "Well-maintained landscaping throughout.",
        listing_url="https://mock.example.com/MOCK002",
        agent_name="James Okello", agent_phone="760-555-0102",
        agent_email="jokello@coastalre.example.com",
    ),
    # 3 — OWTS in description
    Listing(
        listing_id="MOCK003", mls_number="NDP2600003",
        list_date=date(2026, 6, 4), list_price=1_100_000,
        address_line="3305 El Camino Real", city="Rancho Santa Fe",
        state="CA", zip_code="92067",
        beds=5, baths=4.0, sqft=3400,
        sewer=[],
        public_remarks="Sprawling estate on 2 acres. OWTS permit on file. "
                       "Newer roof, solar, and EV charger.",
        listing_url="https://mock.example.com/MOCK003",
        agent_name="Sandra Lim", agent_phone="619-555-0103",
        agent_email="slim@eliteprop.example.com",
    ),
    # 4 — "on-site wastewater" in description
    Listing(
        listing_id="MOCK004", mls_number=None,
        list_date=date(2026, 6, 5), list_price=780_000,
        address_line="890 Paseo Delicias", city="Rancho Santa Fe",
        state="CA", zip_code="92067",
        beds=3, baths=2.5, sqft=2100,
        sewer=[],
        public_remarks="Cozy hillside home with panoramic views. "
                       "On-site wastewater system installed 2019. Propane cooking.",
        listing_url=None,
        agent_name="Carlos Vega", agent_phone="858-555-0104",
        agent_email="cvega@sdpremier.example.com",
    ),
    # 5 — both structured AND description match (no double-count expected)
    Listing(
        listing_id="MOCK005", mls_number="NDP2600005",
        list_date=date(2026, 6, 6), list_price=1_575_000,
        address_line="22 Whispering Pines Rd", city="Rancho Santa Fe",
        state="CA", zip_code="92091",
        beds=5, baths=4.5, sqft=4200,
        sewer=["Septic Tank"],
        public_remarks="Elegant custom build on 3 acres. Septic recently pumped and inspected. "
                       "Resort-style pool and outdoor kitchen.",
        listing_url="https://mock.example.com/MOCK005",
        agent_name="Priya Nair", agent_phone="858-555-0105",
        agent_email="pnair@luxurysd.example.com",
    ),
    # 6 — negation: "no septic" near keyword → should NOT match
    Listing(
        listing_id="MOCK006", mls_number="NDP2600006",
        list_date=date(2026, 6, 7), list_price=950_000,
        address_line="567 Olivenhain Rd", city="Encinitas",
        state="CA", zip_code="92024",
        beds=4, baths=3.0, sqft=2300,
        sewer=[],
        public_remarks="Beautifully updated home. No septic — public sewer connected. "
                       "New kitchen and baths.",
        listing_url="https://mock.example.com/MOCK006",
        agent_name="Tom Hartley", agent_phone="760-555-0106",
        agent_email="thartley@norcounty.example.com",
    ),
    # 7 — negation: "sewer connected" near "septic" → should NOT match
    Listing(
        listing_id="MOCK007", mls_number="NDP2600007",
        list_date=date(2026, 6, 8), list_price=1_050_000,
        address_line="1200 Cancha De Golf", city="Rancho Santa Fe",
        state="CA", zip_code="92091",
        beds=4, baths=3.5, sqft=2950,
        sewer=[],
        public_remarks="Spacious retreat. Septic was removed; now on city sewer. "
                       "Upgraded electrical and HVAC.",
        listing_url="https://mock.example.com/MOCK007",
        agent_name="Angela Brooks", agent_phone="858-555-0107",
        agent_email="abrooks@premsd.example.com",
    ),
    # 8 — structured: Cesspool → match
    Listing(
        listing_id="MOCK008", mls_number="NDP2600008",
        list_date=date(2026, 6, 9), list_price=699_000,
        address_line="33 Corte Villosa", city="Encinitas",
        state="CA", zip_code="92024",
        beds=3, baths=2.0, sqft=1400,
        sewer=["Cesspool"],
        public_remarks="Vintage character home close to beach. Large backyard.",
        listing_url="https://mock.example.com/MOCK008",
        agent_name="Derek Moss", agent_phone="760-555-0108",
        agent_email="dmoss@coastline.example.com",
    ),
    # 9 — Public Sewer, no description keywords → NO match
    Listing(
        listing_id="MOCK009", mls_number="NDP2600009",
        list_date=date(2026, 6, 10), list_price=825_000,
        address_line="4490 Ponderosa Ave", city="Encinitas",
        state="CA", zip_code="92024",
        beds=3, baths=2.0, sqft=1750,
        sewer=["Public Sewer"],
        public_remarks="Move-in ready! Remodeled kitchen, new flooring, and fresh paint.",
        listing_url="https://mock.example.com/MOCK009",
        agent_name="Wendy Park", agent_phone="619-555-0109",
        agent_email="wpark@sdcoastal.example.com",
    ),
    # 10 — no sewer field, no keywords → NO match
    Listing(
        listing_id="MOCK010", mls_number=None,
        list_date=date(2026, 6, 11), list_price=None,
        address_line="7701 Linea Del Cielo", city="Rancho Santa Fe",
        state="CA", zip_code="92067",
        beds=6, baths=5.0, sqft=5800,
        sewer=[],
        public_remarks="Grand estate on gated 5-acre parcel. Chef's kitchen, wine cellar, "
                       "theater room, and tennis court. Price upon request.",
        listing_url=None,
        agent_name="Helena Grant", agent_phone="858-555-0110",
        agent_email="hgrant@estatesocal.example.com",
    ),
]
# fmt: on


class MockProvider:
    """Returns canned sample data for local dev and CI. Ignores zip_codes and since."""

    def fetch_listings(self, zip_codes: list[str], since: datetime) -> list[Listing]:
        return list(_LISTINGS)
