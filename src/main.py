"""
Septic listing agent — CLI entrypoint and pipeline orchestrator.

Usage:
    python -m src.main --provider mock --dry-run [-v]
    python -m src.main --provider mock --to me@example.com [-v]
"""
from __future__ import annotations

import argparse
import logging
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from tenacity import Retrying, stop_after_attempt, wait_chain, wait_fixed

from src.config import load_config
from src.email_sender import SmtpConfigError, send_report
from src.enrichment.owner import enrich_owners
from src.filters.septic import is_septic
from src.report import MatchResult, build_csv, build_html, build_plain, build_subject, csv_filename
from src.state_store import add_listings, filter_new, load_state, save_state

_ROOT = Path(__file__).parent.parent
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory log capture for error-email payloads
# ---------------------------------------------------------------------------

class _LogCapture(logging.Handler):
    """Keeps the last N formatted log lines in memory."""

    def __init__(self, maxlines: int = 200) -> None:
        super().__init__()
        self._lines: list[str] = []
        self._max = maxlines

    def emit(self, record: logging.LogRecord) -> None:
        self._lines.append(self.format(record))
        if len(self._lines) > self._max:
            self._lines.pop(0)

    def tail(self, n: int = 50) -> str:
        return "\n".join(self._lines[-n:])


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(log_level: int, log_path: Path) -> _LogCapture:
    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    stream_h = logging.StreamHandler(sys.stdout)
    stream_h.setFormatter(fmt)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_h = logging.FileHandler(log_path)
    file_h.setFormatter(fmt)

    capture = _LogCapture()
    capture.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(log_level)
    for h in (stream_h, file_h, capture):
        root.addHandler(h)

    return capture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_provider(name: str):
    if name == "mock":
        from src.providers.mock import MockProvider
        return MockProvider()
    raise ValueError(f"Unknown provider: {name!r}")


def _actions_run_url() -> str | None:
    server = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    repo = os.getenv("GITHUB_REPOSITORY")
    run_id = os.getenv("GITHUB_RUN_ID")
    if repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return None


def _try_send_error_email(recipients: list[str], subject: str, body: str) -> None:
    """Best-effort plain-text error notification.  Never raises."""
    try:
        host = os.getenv("SMTP_HOST", "")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        from_addr = os.getenv("EMAIL_FROM", "")
        if not all([host, user, password, from_addr]):
            logger.warning("SMTP not configured — cannot send error email")
            return
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)
        with smtplib.SMTP(host, port) as s:
            s.ehlo()
            s.starttls()
            s.login(user, password)
            s.send_message(msg)
        logger.info("Error email sent to %s", recipients)
    except Exception as exc:
        logger.warning("Could not send error email: %s", exc)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Septic listing agent")
    p.add_argument(
        "--provider", required=True, choices=["mock"],
        help="Data provider to use (mock; real providers added later)",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Run full pipeline but skip email; write CSV to out/ instead",
    )
    p.add_argument(
        "--to", metavar="ADDRESS",
        help="Override recipient address (overrides config/recipients.yml)",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable DEBUG-level logging",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()
    run_dt = datetime.now(timezone.utc)
    log_path = _ROOT / "logs" / f"{run_dt.date().isoformat()}.log"
    capture = _setup_logging(
        logging.DEBUG if args.verbose else logging.INFO,
        log_path,
    )

    logger.info(
        "Run started  provider=%s  dry_run=%s  date=%s",
        args.provider, args.dry_run, run_dt.date(),
    )

    # 1 — Config
    cfg = load_config()
    recipients = [args.to] if args.to else cfg.recipients
    logger.debug("ZIP codes: %s", cfg.zip_codes)
    logger.debug("Recipients: %s", recipients)

    # 2 — State
    state = load_state()
    since = state.fetch_since()
    logger.info(
        "State loaded  last_run_utc=%s  seen_ids=%d  fetch_since=%s",
        state.last_run_utc.isoformat(), len(state.listing_ids), since.isoformat(),
    )

    # 3 — Fetch (3 retries: 1 s → 4 s → 16 s)
    provider = _make_provider(args.provider)
    try:
        for attempt in Retrying(
            stop=stop_after_attempt(4),
            wait=wait_chain(wait_fixed(1), wait_fixed(4), wait_fixed(16)),
            reraise=True,
        ):
            with attempt:
                listings = provider.fetch_listings(cfg.zip_codes, since)
    except Exception as exc:
        logger.error("Provider fetch failed after retries: %s", exc)
        _try_send_error_email(
            recipients,
            f"[septic-agent] Provider error on {run_dt.date()}",
            (
                f"Provider '{args.provider}' fetch failed:\n{exc}\n\n"
                f"Last 50 log lines:\n\n{capture.tail(50)}"
            ),
        )
        sys.exit(1)

    logger.info("Fetched %d listing(s) from provider", len(listings))

    # 4 — Drop already-seen listings
    new_listings = filter_new(listings, state)
    logger.info(
        "New (unseen): %d  |  already seen (skipped): %d",
        len(new_listings), len(listings) - len(new_listings),
    )

    # 5 — Septic filter
    matches: list[MatchResult] = []
    for listing in new_listings:
        matched, reason, snippet = is_septic(listing, cfg.keywords)
        if matched:
            matches.append(MatchResult(listing=listing, reason=reason, snippet=snippet))
    logger.info("Septic matches: %d / %d new listing(s)", len(matches), len(new_listings))

    # 6 — Owner enrichment (non-fatal)
    if cfg.owner_api_key:
        logger.info("Running owner enrichment on %d match(es)", len(matches))
        try:
            enriched_listings = enrich_owners([m.listing for m in matches], cfg.owner_api_key)
            by_id = {l.listing_id: l for l in enriched_listings}
            matches = [
                MatchResult(
                    listing=by_id.get(m.listing.listing_id, m.listing),
                    reason=m.reason,
                    snippet=m.snippet,
                )
                for m in matches
            ]
        except Exception as exc:
            logger.warning("Owner enrichment failed (continuing): %s", exc)
    else:
        logger.info("OWNER_API_KEY not set — skipping owner enrichment")

    # 7 — Build report artifacts
    actions_url = _actions_run_url()
    subject = build_subject(run_dt.date(), len(matches))
    html_body = build_html(matches, cfg.zip_codes, len(listings), run_dt, actions_url)
    text_body = build_plain(matches, cfg.zip_codes, len(listings), run_dt, actions_url)

    out_dir = _ROOT / "out"
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / csv_filename(run_dt.date())
    csv_path.write_text(build_csv(matches), encoding="utf-8")
    logger.debug("CSV written → %s", csv_path)

    # 8 — Send or dry-run
    if args.dry_run:
        logger.info("DRY RUN — email not sent, CSV at %s", csv_path)
        print(f"\nSubject: {subject}")
        print("=" * 60)
        lines = text_body.splitlines()
        for line in lines[:20]:
            print(line)
        if len(lines) > 20:
            print(f"  … ({len(lines) - 20} more lines)")
        print()
    else:
        logger.info("Sending email to %s", recipients)
        try:
            send_report(recipients, subject, html_body, text_body, csv_path)
            logger.info("Email sent successfully")
        except (SmtpConfigError, smtplib.SMTPException, OSError) as exc:
            logger.error("Email send failed: %s", exc)
            logger.error("Report saved to %s — upload as artifact", csv_path)
            sys.exit(1)

    # 9 — Persist state (skipped in dry-run to keep runs idempotent)
    if not args.dry_run:
        add_listings(state, listings, run_dt)
        save_state(state)
        logger.info(
            "State saved  total_seen_ids=%d  last_run_utc=%s",
            len(state.listing_ids), state.last_run_utc.isoformat(),
        )
    else:
        logger.info("DRY RUN — state not updated")

    logger.info("Run complete")


if __name__ == "__main__":
    main()
