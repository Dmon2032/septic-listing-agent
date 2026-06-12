from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime

from src.models import Listing


@dataclass
class MatchResult:
    listing: Listing
    reason: str
    snippet: str | None


# ---------------------------------------------------------------------------
# Subject + filename helpers
# ---------------------------------------------------------------------------

def build_subject(run_date: date, n_matches: int) -> str:
    """'Septic listings — week of Jun 9, 2026 — 6 new'"""
    month = run_date.strftime("%b")
    return f"Septic listings — week of {month} {run_date.day}, {run_date.year} — {n_matches} new"


def csv_filename(run_date: date) -> str:
    return f"septic_listings_{run_date.isoformat()}.csv"


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

_CSV_COLUMNS = [
    "listing_id", "list_date", "address_line", "city", "state", "zip_code",
    "list_price", "beds", "baths", "sqft", "sewer_field", "match_reason",
    "description_snippet", "listing_url",
    "agent_name", "agent_phone", "agent_email",
    "homeowner_name",
]


def build_csv(matches: list[MatchResult]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_CSV_COLUMNS)
    for m in matches:
        l = m.listing
        writer.writerow([
            l.listing_id,
            l.list_date.isoformat(),
            l.address_line,
            l.city,
            l.state,
            l.zip_code,
            l.list_price if l.list_price is not None else "",
            l.beds if l.beds is not None else "",
            l.baths if l.baths is not None else "",
            l.sqft if l.sqft is not None else "",
            "; ".join(l.sewer),
            m.reason,
            m.snippet or "",
            l.listing_url or "",
            l.agent_name or "",
            l.agent_phone or "",
            l.agent_email or "",
            l.homeowner_name or "",
        ])
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Formatting helpers (shared by HTML and plain)
# ---------------------------------------------------------------------------

def _fmt_price(price: int | None) -> str:
    return f"${price:,}" if price is not None else "—"


def _fmt_detail(l: Listing) -> str:
    parts = []
    if l.beds is not None:
        parts.append(f"{l.beds:g} bd")
    if l.baths is not None:
        parts.append(f"{l.baths:g} ba")
    if l.sqft is not None:
        parts.append(f"{l.sqft:,} sqft")
    return " / ".join(parts) if parts else "—"


def _esc(text: str) -> str:
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# HTML body
# ---------------------------------------------------------------------------

def build_html(
    matches: list[MatchResult],
    zip_codes: list[str],
    n_fetched: int,
    run_dt: datetime,
    actions_run_url: str | None = None,
) -> str:
    n = len(matches)
    run_str = run_dt.strftime("%Y-%m-%d %H:%M UTC")

    intro = (
        f"Scanned {len(zip_codes)} ZIP code{'s' if len(zip_codes) != 1 else ''} "
        f"({_esc(', '.join(zip_codes))}). "
        f"Fetched {n_fetched} listing{'s' if n_fetched != 1 else ''}. "
        f"Found <strong>{n}</strong> new septic match{'es' if n != 1 else ''}."
    )

    if n == 0:
        body_section = "<p>No new septic listings this week.</p>"
    else:
        rows: list[str] = []
        for m in matches[:10]:
            l = m.listing
            addr = _esc(f"{l.address_line}, {l.city}, {l.state} {l.zip_code}")
            if l.listing_url:
                addr = f'<a href="{_esc(l.listing_url)}">{addr}</a>'
            rows.append(
                "<tr>"
                f"<td>{addr}</td>"
                f"<td>{_esc(_fmt_price(l.list_price))}</td>"
                f"<td>{_esc(_fmt_detail(l))}</td>"
                f"<td>{_esc(l.agent_name or '—')}</td>"
                f"<td>{_esc(l.agent_phone or '—')}</td>"
                f"<td><small>{_esc(m.snippet or '—')}</small></td>"
                "</tr>"
            )

        overflow = ""
        if n > 10:
            overflow = f"<p><em>…and {n - 10} more in the attached CSV.</em></p>"

        body_section = (
            '<table border="1" cellpadding="5" cellspacing="0"'
            ' style="border-collapse:collapse;font-size:13px;">\n'
            "<thead style=\"background:#f0f0f0;\">\n"
            "  <tr>"
            "<th>Address</th>"
            "<th>Price</th>"
            "<th>Beds / Baths / Sqft</th>"
            "<th>Agent</th>"
            "<th>Phone</th>"
            "<th>Snippet</th>"
            "</tr>\n"
            "</thead>\n"
            "<tbody>\n"
            + "\n".join(rows)
            + "\n</tbody>\n</table>\n"
            + overflow
            + "<p>Full list attached as CSV.</p>\n"
        )

    footer_parts = [_esc(run_str)]
    if actions_run_url:
        footer_parts.append(f'<a href="{_esc(actions_run_url)}">GitHub Actions run</a>')
    footer = " &nbsp;|&nbsp; ".join(footer_parts)

    return (
        "<!DOCTYPE html>\n"
        "<html>\n"
        '<body style="font-family:Arial,sans-serif;font-size:14px;color:#333;">\n'
        f"<p>{intro}</p>\n"
        f"{body_section}"
        "<hr>\n"
        f"<p><small>{footer}</small></p>\n"
        "</body>\n"
        "</html>"
    )


# ---------------------------------------------------------------------------
# Plain-text fallback
# ---------------------------------------------------------------------------

def build_plain(
    matches: list[MatchResult],
    zip_codes: list[str],
    n_fetched: int,
    run_dt: datetime,
    actions_run_url: str | None = None,
) -> str:
    n = len(matches)
    run_str = run_dt.strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        f"Scanned {len(zip_codes)} ZIP code{'s' if len(zip_codes) != 1 else ''} "
        f"({', '.join(zip_codes)}). "
        f"Fetched {n_fetched} listing{'s' if n_fetched != 1 else ''}. "
        f"Found {n} new septic match{'es' if n != 1 else ''}.",
        "",
    ]

    if n == 0:
        lines.append("No new septic listings this week.")
    else:
        for i, m in enumerate(matches[:10], 1):
            l = m.listing
            lines.append(
                f"{i}. {l.address_line}, {l.city}, {l.state} {l.zip_code}"
                f"  |  {_fmt_price(l.list_price)}  |  {_fmt_detail(l)}"
            )
            agent_parts = [p for p in [l.agent_name, l.agent_phone] if p]
            if agent_parts:
                lines.append(f"   Agent: {' | '.join(agent_parts)}")
            if m.snippet:
                lines.append(f'   "{m.snippet}"')
            lines.append("")

        if n > 10:
            lines += [f"…and {n - 10} more. See attached CSV for the full list.", ""]

        lines.append("Full list attached as CSV.")

    lines += ["", "---"]
    footer = run_str
    if actions_run_url:
        footer += f"  |  {actions_run_url}"
    lines.append(footer)

    return "\n".join(lines)
