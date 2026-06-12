"""
SMTP email sender.

Uses only stdlib smtplib + email.message.EmailMessage — no third-party email lib.

MIME structure produced:
  multipart/mixed
  ├── multipart/alternative
  │   ├── text/plain   (fallback)
  │   └── text/html    (preferred)
  └── text/csv         (attachment, disposition=attachment)
"""
from __future__ import annotations

import argparse
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class SmtpConfigError(ValueError):
    """Raised when required SMTP environment variables are missing."""


def _smtp_config() -> tuple[str, int, str, str, str]:
    """Return (host, port, user, password, from_addr).

    Raises SmtpConfigError if any required variable is absent or empty.
    """
    host = os.getenv("SMTP_HOST", "")
    port_str = os.getenv("SMTP_PORT", "587")
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("EMAIL_FROM", "")

    missing = [
        name for name, val in [
            ("SMTP_HOST", host),
            ("SMTP_USER", user),
            ("SMTP_PASSWORD", password),
            ("EMAIL_FROM", from_addr),
        ]
        if not val
    ]
    if missing:
        raise SmtpConfigError(
            f"Missing required SMTP environment variable(s): {', '.join(missing)}"
        )

    return host, int(port_str), user, password, from_addr


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_report(
    recipients: list[str],
    subject: str,
    html_body: str,
    text_body: str,
    csv_path: Path,
) -> None:
    """Send the weekly report email with a CSV attachment.

    Raises:
        SmtpConfigError   — SMTP env vars missing or empty.
        smtplib.SMTPException — connection or send failure; caller should
                               catch this and write the fallback artifact.
    """
    host, port, user, password, from_addr = _smtp_config()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(recipients)

    # Plain-text base; add_alternative wraps both in multipart/alternative.
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    # add_attachment promotes the root to multipart/mixed, keeping the
    # multipart/alternative body intact as the first child.
    csv_text = csv_path.read_text(encoding="utf-8")
    msg.add_attachment(
        csv_text,
        subtype="csv",
        filename=csv_path.name,
        charset="utf-8",
    )

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


# ---------------------------------------------------------------------------
# __main__ — quick SMTP connectivity test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send a one-line test email to verify SMTP credentials."
    )
    parser.add_argument("--to", required=True, metavar="ADDRESS",
                        help="Recipient email address")
    args = parser.parse_args()

    host, port, user, password, from_addr = _smtp_config()

    msg = EmailMessage()
    msg["Subject"] = "Septic listing agent — SMTP test"
    msg["From"] = from_addr
    msg["To"] = args.to
    msg.set_content(
        "This is a test email from the septic listing agent.\n"
        "If you received this, your SMTP credentials are working correctly.\n"
    )

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.send_message(msg)

    print(f"✓ Test email sent to {args.to} via {host}:{port}")
