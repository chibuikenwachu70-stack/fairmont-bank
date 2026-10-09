"""Brevo SMTP helper for NewBankSite.

This module sends only explicit, authorized test/support messages. It does not
create or assert banking transactions, balances, approvals, or payment events.
"""
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp-relay.brevo.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "").strip()
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "").strip()
MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "").strip()
MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}


def send_email(recipient: str, subject: str, text_body: str) -> None:
    """Send a plain-text email; raises a useful exception on configuration/delivery failure."""
    if not all((MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER)):
        raise RuntimeError(
            "Email settings are incomplete. Check MAIL_SERVER, MAIL_USERNAME, "
            "MAIL_PASSWORD, and MAIL_DEFAULT_SENDER in your .env file."
        )
    if not recipient or "@" not in recipient:
        raise ValueError("Enter a valid recipient email address.")

    msg = EmailMessage()
    msg["From"] = MAIL_DEFAULT_SENDER
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(text_body)

    with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=25) as smtp:
        smtp.ehlo()
        if MAIL_USE_TLS:
            smtp.starttls()
            smtp.ehlo()
        smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
        smtp.send_message(msg)
