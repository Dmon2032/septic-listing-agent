from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Listing(BaseModel):
    listing_id: str
    mls_number: str | None
    list_date: date
    list_price: int | None
    address_line: str
    city: str
    state: str
    zip_code: str
    beds: float | None
    baths: float | None
    sqft: int | None
    sewer: list[str] = []
    public_remarks: str = ""
    listing_url: str | None
    agent_name: str | None
    agent_phone: str | None
    agent_email: str | None
    homeowner_name: str | None = None
