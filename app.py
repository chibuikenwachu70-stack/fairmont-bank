from flask import Flask, render_template, render_template_string, request, session, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from flask_login import UserMixin
from flask_login import login_user
from flask_login import LoginManager
from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import string
import csv
import io
import json
import urllib.request
import urllib.error
import os
from datetime import datetime, timezone, timedelta
import re
import smtplib
from email.message import EmailMessage

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


app = Flask(__name__)


def send_bank_email(recipient_email, subject, body, html_body=None):
    """Send a transparent bank notification using Brevo's HTTPS API.

    Render free services may block outbound SMTP ports. The Brevo API uses
    HTTPS (port 443), avoiding SMTP connectivity while keeping delivery errors
    from crashing the request handler.
    """
    recipient_email = (recipient_email or "").strip()
    if not recipient_email or "@" not in recipient_email:
        app.logger.warning("EMAIL NOT SENT: recipient email is missing or invalid.")
        return False

    api_key = os.getenv("BREVO_API_KEY", "").strip()
    sender_email = os.getenv("MAIL_DEFAULT_SENDER", "").strip()
    if not api_key or not sender_email:
        app.logger.error(
            "EMAIL NOT SENT: configure BREVO_API_KEY and MAIL_DEFAULT_SENDER in Render."
        )
        return False

    # This application is a banking-software. Make that clear in
    # notifications so messages cannot be mistaken for proof of real transfers.
    safe_subject = str(subject or "Account notification").strip()
    if not safe_subject.upper().startswith("[BANK]"):
        safe_subject = "[BANK] " + safe_subject

    disclosure = (
        "SIMULATED BANKING SOFTWARE NOTICE: This email reports activity "
        "recorded in the Fairmont Bank."
    )

    text_body = disclosure + "\n\n" + str(body or "").strip()
    if html_body:
        html_content = (
            '<div style="margin:0 auto 18px;padding:12px 16px;max-width:600px;'
            'background:#fff4d6;border:1px solid #e6c56b;color:#5b4300;'
            'font: bold 13px Arial,sans-serif;line-height:1.5">'
            + disclosure
            + '</div>' + str(html_body)
        )
    else:
        html_content = None

    payload = {
        "sender": {"name": "Fairmont Bank", "email": sender_email},
        "to": [{"email": recipient_email}],
        "subject": safe_subject,
        "textContent": text_body,
    }
    if html_content:
        payload["htmlContent"] = html_content

    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if 200 <= response.status < 300:
                app.logger.info("EMAIL ACCEPTED by Brevo API for %s", recipient_email)
                return True
            app.logger.error("EMAIL FAILED: Brevo API returned HTTP %s", response.status)
            return False
    except urllib.error.HTTPError as exc:
        # Avoid logging request headers or secrets. Brevo's response body can
        # explain sender verification or account issues without exposing keys.
        try:
            error_body = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            error_body = "response body unavailable"
        app.logger.error("EMAIL FAILED: Brevo API HTTP %s: %s", exc.code, error_body)
        return False
    except Exception as exc:
        app.logger.error("EMAIL FAILED for %s: %s: %s", recipient_email, type(exc).__name__, exc)
        return False


def send_branded_customer_email(
    customer,
    subject,
    eyebrow,
    heading,
    message_text,
    details=None,
):
    """Send a branded HTML and plain-text customer email with a bank disclosure."""
    if customer is None or not getattr(customer, "email", None):
        return False

    details = details or []
    text_lines = [
        "FAIRMONT BANK — ACCOUNT SERVICES",
        "",
        str(heading),
        "",
        f"Dear {customer.full_name},",
        "",
        str(message_text),
        "",
    ]
    for label, value in details:
        text_lines.append(f"{label}: {value}")
    text_lines.extend([
        "",
        "For assistance, contact support@fairmontbank.com.",
        "",
        "Kind regards,",
        "Fairmont Bank",
        "Account Services",
    ])

    html_body = render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>{{ heading }}</title>
        </head>
        <body style="margin:0;padding:0;background:#f2f5f9;font-family:Arial,Helvetica,sans-serif;color:#253247;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f2f5f9;padding:28px 10px;">
            <tr><td align="center">
              <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="width:100%;max-width:600px;background:#ffffff;border:1px solid #e1e7ef;border-radius:12px;overflow:hidden;">
                <tr><td style="background:#102747;padding:26px 28px;text-align:center;">
                  {% if logo_url %}<img src="{{ logo_url }}" alt="Fairmont Bank" width="170" style="display:block;max-width:170px;width:100%;height:auto;margin:0 auto 12px;border:0;">{% else %}<div style="font-size:24px;font-weight:700;letter-spacing:2px;color:#ffffff;">FAIRMONT BANK</div>{% endif %}
                  <div style="font-size:11px;letter-spacing:2px;color:#d9bd78;margin-top:8px;">ACCOUNT SERVICES</div>
                  <div style="height:3px;width:58px;background:#c5a45d;margin:18px auto 0;"></div>
                </td></tr>
                <tr><td style="padding:30px 28px 12px;">
                  <div style="font-size:11px;font-weight:700;letter-spacing:1.5px;color:#9a772f;">{{ eyebrow|upper }}</div>
                  <h1 style="font-size:25px;line-height:1.3;color:#102747;margin:10px 0 18px;">{{ heading }}</h1>
                  <p style="font-size:15px;line-height:1.8;margin:0 0 14px;">Dear {{ customer.full_name }},</p>
                  <p style="font-size:14px;line-height:1.8;color:#536174;margin:0 0 22px;white-space:pre-line;">{{ message_text }}</p>
                </td></tr>
                {% if details %}
                <tr><td style="padding:0 28px 24px;">
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e1e7ef;border-radius:8px;">
                    <tr><td colspan="2" style="padding:13px 16px;background:#f6f8fb;color:#102747;font-size:12px;font-weight:700;letter-spacing:1px;">DETAILS</td></tr>
                    {% for label, value in details %}
                    <tr>
                      <td style="padding:12px 16px;border-top:1px solid #edf0f4;color:#68768a;font-size:13px;">{{ label }}</td>
                      <td style="padding:12px 16px;border-top:1px solid #edf0f4;color:#102747;font-size:13px;font-weight:700;text-align:right;word-break:break-word;">{{ value }}</td>
                    </tr>
                    {% endfor %}
                  </table>
                </td></tr>
                {% endif %}
                <tr><td style="padding:0 28px 28px;">
                  <p style="font-size:13px;line-height:1.8;color:#536174;margin:0;">If you need assistance, contact <a href="mailto:support@fairmontbank.com" style="color:#9a772f;text-decoration:none;font-weight:700;">support@fairmontbank.com</a>.</p>
                  <p style="font-size:13px;line-height:1.8;color:#536174;margin:18px 0 0;">Kind regards,<br><strong style="color:#102747;">Fairmont Bank</strong><br>Account Services</p>
                </td></tr>
                <tr><td style="background:#f6f8fb;border-top:1px solid #e1e7ef;padding:18px 24px;text-align:center;">
                  <p style="font-size:11px;line-height:1.7;color:#7b8797;margin:0;">This email is generated by a banking software.
                  <p style="font-size:11px;color:#9aa4b2;margin:10px 0 0;">&copy; Fairmont Bank. All rights reserved.</p>
                </td></tr>
              </table>
            </td></tr>
          </table>
        </body>
        </html>
        """,
        customer=customer,
        eyebrow=eyebrow,
        heading=heading,
        message_text=message_text,
        details=details,
        logo_url=os.getenv("BANK_LOGO_URL", "").strip(),
    )
    return send_bank_email(
        customer.email,
        subject,
        "\n".join(text_lines),
        html_body=html_body,
    )
def send_branded_recipient_email(
    recipient_email,
    recipient_name,
    subject,
    eyebrow,
    heading,
    message_text,
    details=None,
):
    """Send a branded HTML email to an external transfer recipient."""

    if not recipient_email:
        return False

    details = details or []

    text_lines = [
        "FAIRMONT BANK - ACCOUNT SERVICES",
        "",
        heading,
        "",
        f"Dear {recipient_name or 'Recipient'},",
        "",
        message_text,
        "",
    ]

    for label, value in details:
        text_lines.append(f"{label}: {value}")

    text_lines.extend([
        "",
        "This notification reflects the status recorded in the application.",
        "It does not independently confirm that external funds were credited.",
        "",
        "Kind regards,",
        "Fairmont Bank",
        "Account Services",
    ])

    html_body = render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>{{ heading }}</title>
        </head>

        <body style="margin:0;padding:0;background:#f2f5f9;
                     font-family:Arial,Helvetica,sans-serif;color:#253247;">

          <table role="presentation" width="100%" cellspacing="0"
                 cellpadding="0" style="background:#f2f5f9;padding:28px 10px;">
            <tr>
              <td align="center">

                <table role="presentation" width="600" cellspacing="0"
                       cellpadding="0"
                       style="width:100%;max-width:600px;background:#ffffff;
                              border:1px solid #e1e7ef;border-radius:12px;
                              overflow:hidden;">

                  <tr>
                    <td style="background:#102747;padding:26px 28px;text-align:center;">
                      {% if logo_url %}
                      <img src="{{ logo_url }}" alt="Fairmont Bank" width="170"
                           style="display:block;max-width:170px;width:100%;height:auto;margin:0 auto 12px;border:0;">
                      {% else %}
                      <div style="font-size:24px;font-weight:700;letter-spacing:2px;color:#ffffff;">FAIRMONT BANK</div>
                      {% endif %}
                      <div style="font-size:11px;letter-spacing:2px;
                                  color:#d9bd78;margin-top:8px;">
                        ACCOUNT SERVICES
                      </div>
                      <div style="height:3px;width:58px;background:#c5a45d;
                                  margin:18px auto 0;"></div>
                    </td>
                  </tr>

                  <tr>
                    <td style="padding:30px 28px 12px;">
                      <div style="font-size:11px;font-weight:700;
                                  letter-spacing:1.5px;color:#9a772f;">
                        {{ eyebrow|upper }}
                      </div>

                      <h1 style="font-size:25px;line-height:1.3;
                                 color:#102747;margin:10px 0 18px;">
                        {{ heading }}
                      </h1>

                      <p style="font-size:15px;line-height:1.8;margin:0 0 14px;">
                        Dear {{ recipient_name or "Recipient" }},
                      </p>

                      <p style="font-size:14px;line-height:1.8;color:#536174;
                                margin:0 0 22px;white-space:pre-line;">
                        {{ message_text }}
                      </p>
                    </td>
                  </tr>

                  {% if details %}
                  <tr>
                    <td style="padding:0 28px 24px;">
                      <table role="presentation" width="100%" cellspacing="0"
                             cellpadding="0"
                             style="border:1px solid #e1e7ef;border-radius:8px;">

                        <tr>
                          <td colspan="2"
                              style="padding:13px 16px;background:#f6f8fb;
                                     color:#102747;font-size:12px;
                                     font-weight:700;letter-spacing:1px;">
                            TRANSFER DETAILS
                          </td>
                        </tr>

                        {% for label, value in details %}
                        <tr>
                          <td style="padding:12px 16px;border-top:1px solid #edf0f4;
                                     color:#68768a;font-size:13px;">
                            {{ label }}
                          </td>
                          <td style="padding:12px 16px;border-top:1px solid #edf0f4;
                                     color:#102747;font-size:13px;font-weight:700;
                                     text-align:right;word-break:break-word;">
                            {{ value }}
                          </td>
                        </tr>
                        {% endfor %}

                      </table>
                    </td>
                  </tr>
                  {% endif %}

                  <tr>
                    <td style="padding:0 28px 28px;">
                      <p style="font-size:13px;line-height:1.8;color:#536174;">
                        For assistance, contact
                        <a href="mailto:support@fairmontbank.com"
                           style="color:#9a772f;text-decoration:none;font-weight:700;">
                          support@fairmontbank.com
                        </a>.
                      </p>

                      <p style="font-size:13px;line-height:1.8;color:#536174;">
                        Kind regards,<br>
                        <strong style="color:#102747;">Fairmont Bank</strong><br>
                        Account Services
                      </p>
                    </td>
                  </tr>

                  <tr>
                    <td style="background:#f6f8fb;border-top:1px solid #e1e7ef;
                               padding:18px 24px;text-align:center;">
                      <p style="font-size:11px;line-height:1.7;color:#7b8797;">
                        
                      </p>
                      <p style="font-size:11px;color:#9aa4b2;">
                        Fairmont Bank - Account Services
                      </p>
                    </td>
                  </tr>

                </table>
              </td>
            </tr>
          </table>
        </body>
        </html>
        """,
        recipient_name=recipient_name or "Recipient",
        eyebrow=eyebrow,
        heading=heading,
        message_text=message_text,
        details=details,
        logo_url=os.getenv("BANK_LOGO_URL", "").strip(),
    )

    return send_bank_email(
        recipient_email,
        subject,
        "\n".join(text_lines),
        html_body=html_body,
    )

def send_account_status_email(customer, status):
    """Notify a customer after their account application status is saved."""
    normalized = (status or "").strip().lower()
    if normalized == "active":
        subject = "Account Application Approved"
        eyebrow = "Application Update"
        heading = "Your Application Has Been Approved"
        message_text = (
            "Your account application has been approved in the Fairmont Bank "
            "fairmontbank.You can sign in to review the account features."
        )
    elif normalized == "rejected":
        subject = "Account Application Update"
        eyebrow = "Application Update"
        heading = "Your Application Status Has Been Updated"
        message_text = (
            "Your account application has been marked as rejected in the Fairmont "
            "Bank software notice. If you believe this is an error, please "
            "contact support for assistance."
        )
    else:
        subject = "Account Application Update"
        eyebrow = "Application Update"
        heading = "Your Application Status Has Changed"
        message_text = f"Your application status is now {status}."

    return send_branded_customer_email(
        customer,
        subject,
        eyebrow,
        heading,
        message_text,
        [
            ("Application reference", customer.customer_id),
            ("Account type", customer.account_type),
            ("Application status", status),
        ],
    )


def send_payment_status_email(customer, approval, event="submitted"):
    """Email a clear status update for a submitted, approved, or rejected request."""
    if customer is None or approval is None:
        return False

    status = approval.status or "Pending Approval"
    amount_text = f"£{float(approval.amount or 0):,.2f}"
    details = [
        ("Request reference", approval.payment_reference),
        ("Request type", approval.payment_type),
        ("Amount", amount_text),
        ("Status", status),
    ]
    if approval.rejection_reason:
        details.append(("Reason", approval.rejection_reason))

    if event == "approved":
        subject = "Payment Request Approved"
        heading = "Your Request Has Been Approved"
        message_text = (
            "Your request has been approved and the corresponding entry has been "
            "recorded in this software . This message does not represent "
            "a real-world funds transfer."
        )
    elif event == "rejected":
        subject = "Payment Request Update"
        heading = "Your Request Was Not Approved"
        message_text = (
            "Your request has been marked as rejected in this software."
            "No balance change was made as part of this rejection."
        )
    else:
        subject = "We Received Your Payment Request"
        heading = "Your Request Has Been Received"
        if status == "TCC Verification Required":
            message_text = (
                "Your request has been received and is awaiting the additional "
                "verification step shown on the website. It has not been approved."
            )
        else:
            message_text = (
                "Your request has been recorded and is awaiting review. A pending "
                "request is not a completed transaction."
            )

    return send_branded_customer_email(
        customer,
        subject,
        "Payment Request Update",
        heading,
        message_text,
        details,
    )


def send_transaction_alert(customer, transaction):
    """Send a debit or credit alert only for a transaction already committed as completed."""
    if customer is None or transaction is None:
        return False
    if str(transaction.status or "").strip().lower() not in {
        "completed", "complete", "success", "successful"
    }:
        return False
    if not bool(getattr(customer, "transaction_notifications", True)):
        return False

    direction = (transaction.direction or "").strip().lower()
    if direction not in {"credit", "debit"}:
        return False

    is_credit = direction == "credit"
    subject = (
        "Credit Transaction Alert" if is_credit else "Debit Transaction Alert"
    )
    heading = (
        "Your Account Has Been Credited"
        if is_credit
        else "Your Account Has Been Debited"
    )
    description = (
        getattr(transaction, "description", None)
        or getattr(transaction, "transaction_type", None)
        or "Bank transaction"
    )
    message_text = (
        (
            f"A debit transaction of £{float(transaction.amount or 0):,.2f} "
            "has been recorded on your account.\n\n"
            "Please review the transaction details below. If you do not "
            "recognize this transaction, please contact our support team "
            "at support@fairmontbank.com."
        )
        if not is_credit
        else (
            f"A credit transaction of £{float(transaction.amount or 0):,.2f} "
            "has been recorded on your account.\n\n"
            "Please review the transaction details below. If you have any "
            "questions about this transaction, please contact our support team "
            "at support@fairmontbank.com."
        )
    )
    account_number = getattr(customer, "account_number", "") or ""
    masked_account = ("••••" + account_number[-4:]) if account_number else "Not available"
    created_at = (
        transaction.created_at.strftime("%d %b %Y, %H:%M UTC")
        if transaction.created_at else "Not available"
    )
    sender_name = (
        getattr(transaction, "sender_name", None)
        or getattr(transaction, "counterparty_name", None)
        or "Not specified"
    )
    return send_branded_customer_email(
        customer,
        subject,
        "Transaction Alert",
        heading,
        message_text,
        [
            ("Transaction type", transaction.transaction_type or direction.title()),
            ("Amount", f"£{float(transaction.amount or 0):,.2f}"),
            ("Reference", transaction.transaction_reference),
            ("Description", description),
            ("Sender Name", sender_name or "Not specified"),
            ("Account", masked_account),
            ("Date", created_at),
            ("Status", transaction.status or "Recorded"),
            ("Account Balance", f"£{float(transaction.balance_after or 0):,.2f}"),
        ],
    )

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Customer, int(user_id))

app.config["SECRET_KEY"] = "change-this-before-production"

# Keep the authenticated customer session available while
# navigating between protected customer pages.
app.config["SESSION_PERMANENT"] = True


# =========================================================
# DATABASE
# =========================================================

os.makedirs(app.instance_path, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(app.instance_path, "fairmont.db")
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

import logging

logging.basicConfig(level=logging.INFO)

with app.app_context():
    logging.info(
        "Database backend configured: %s",
        db.engine.dialect.name
    )

# =========================================================
# POSTGRES PAYMENT APPROVAL SEQUENCE REPAIR
# =========================================================

def repair_payment_approvals_sequence():
    """
    Synchronize the PostgreSQL payment_approvals.id sequence
    with the highest existing ID.

    Safe for SQLite: this function does nothing when the
    application is using SQLite.
    """

    try:
        engine_url = str(db.engine.url)

        # Local SQLite database: nothing to repair.
        if not engine_url.startswith(("postgresql://", "postgresql+")):
            return

        from sqlalchemy import text

        db.session.execute(
            text("""
                SELECT setval(
                    pg_get_serial_sequence(
                        'payment_approvals',
                        'id'
                    ),
                    COALESCE(
                        (
                            SELECT MAX(id)
                            FROM payment_approvals
                        ),
                        0
                    ) + 1,
                    false
                )
            """)
        )

        db.session.commit()

        print(
            "PAYMENT APPROVALS SEQUENCE: synchronized successfully."
        )

    except Exception as exc:
        db.session.rollback()

        print(
            "PAYMENT APPROVALS SEQUENCE: repair skipped:",
            exc
        )


# =========================================================
# CUSTOMER MODEL
# =========================================================



# ============================================================
# FAIRmont BANK LIVE CHAT
# Customer-to-Bank Support Chat Models
# ============================================================

class LiveChatConversation(db.Model):
    __tablename__ = "live_chat_conversations"

    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id"),
        nullable=False,
        index=True
    )

    # Browser session identifier used for visitors who are not signed in.
    guest_session_id = db.Column(
        db.String(120),
        nullable=True,
        index=True
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Open"
    )

    subject = db.Column(
        db.String(200),
        nullable=False,
        default="Bank Support"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


class LiveChatMessage(db.Model):
    __tablename__ = "live_chat_messages"

    id = db.Column(db.Integer, primary_key=True)

    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("live_chat_conversations.id"),
        nullable=False,
        index=True
    )

    sender_type = db.Column(
        db.String(20),
        nullable=False
    )

    sender_id = db.Column(
        db.Integer,
        nullable=True
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )




# ============================================================
# FAIRMONT BANK ADMINISTRATION
# Admin authentication model
# ============================================================

class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class Customer(UserMixin, db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )


    account_number = db.Column(
        db.String(12),
        unique=True,
        nullable=True,
        index=True
    )

    full_name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    phone = db.Column(
        db.String(40),
        unique=True,
        nullable=False
    )

    account_type = db.Column(
        db.String(30),
        nullable=False
    )

    country = db.Column(
        db.String(100),
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    account_status = db.Column(
        db.String(30),
        nullable=False,
        default="Active"
    )

    tcc_payment_restriction_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    preferred_language = db.Column(
        db.String(20),
        nullable=False,
        default="English"
    )

    preferred_currency_display = db.Column(
        db.String(10),
        nullable=False,
        default="GBP"
    )

    preferred_date_format = db.Column(
        db.String(30),
        nullable=False,
        default="DD/MM/YYYY"
    )

    account_display_preference = db.Column(
        db.String(30),
        nullable=False,
        default="Standard"
    )

    account_balance = db.Column(
        db.Float,
        nullable=False,
        default=0.0
    )

    bank_statements_locked = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )




# =========================================================
# TRANSACTION MODEL
# =========================================================


    login_otp_enabled = db.Column(db.Boolean, nullable=False, default=False)

    transaction_notifications = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    security_notifications = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    account_notifications = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    promotional_notifications = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )




# =========================================================
# TRANSACTION MODEL
# =========================================================

class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    transaction_reference = db.Column(db.String(40), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.String(20), nullable=False, index=True)
    transaction_type = db.Column(db.String(80), nullable=False)
    direction = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    balance_after = db.Column(db.Float, nullable=False, default=0.0)
    description = db.Column(db.String(255), nullable=False, default="")
    counterparty = db.Column(db.String(150), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="Completed")
    sender_name = db.Column(db.String(150), nullable=True)
    sender_account_number = db.Column(db.String(50), nullable=True)
    sender_bank = db.Column(db.String(150), nullable=True)
    sender_country = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


# =========================================================
# FAIRMONT BANK CUSTOMER INVOICE / BILLING MODEL
# =========================================================

class BankInvoice(db.Model):
    __tablename__ = "bank_invoices"

    id = db.Column(db.Integer, primary_key=True)

    invoice_number = db.Column(
        db.String(40), unique=True, nullable=False, index=True
    )

    customer_id = db.Column(
        db.String(20), nullable=False, index=True
    )

    billing_type = db.Column(
        db.String(100), nullable=False
    )

    description = db.Column(
        db.String(500), nullable=False
    )

    amount = db.Column(db.Float, nullable=False, default=0.0)
    tcc_tax = db.Column(db.Float, nullable=False, default=0.0)
    other_fee = db.Column(db.Float, nullable=False, default=0.0)
    discount = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)

    currency = db.Column(
        db.String(10), nullable=False, default="GBP"
    )

    issue_date = db.Column(
        db.Date, nullable=False, default=lambda: datetime.utcnow().date()
    )

    due_date = db.Column(
        db.Date, nullable=False
    )

    status = db.Column(
        db.String(30), nullable=False, default="Pending"
    )

    payment_method = db.Column(
        db.String(80), nullable=True
    )

    payment_reference = db.Column(
        db.String(100), nullable=True
    )

    billing_note = db.Column(
        db.Text, nullable=True
    )

    created_by = db.Column(
        db.String(80), nullable=True
    )

    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )

    paid_at = db.Column(
        db.DateTime, nullable=True
    )


class CustomerLoginOTP(db.Model):

    __tablename__ = "customer_login_otp"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id"),
        nullable=False,
        index=True
    )

    otp_code = db.Column(
        db.String(6),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    expires_at = db.Column(
        db.DateTime,
        nullable=False
    )

    used = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )


class LoginOTPRecoveryRequest(db.Model):

    __tablename__ = "login_otp_recovery_request"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id"),
        nullable=False
    )

    recovery_code = db.Column(
        db.String(20),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    expires_at = db.Column(
        db.DateTime,
        nullable=False
    )

    used_at = db.Column(
        db.DateTime,
        nullable=True
    )

class Notification(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    notification_type = db.Column(
        db.String(50),
        default="General",
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )


def create_customer_notification(customer_id, title, message,
                                 notification_type="General",
                                 commit=True):
    """Create an in-site notification while respecting customer preferences."""
    customer = Customer.query.filter_by(customer_id=str(customer_id)).first()
    if customer is None:
        return None

    kind = (notification_type or "General").strip().lower()
    preference_by_type = {
        "transaction": "transaction_notifications",
        "security": "security_notifications",
        "account": "account_notifications",
        "promotional": "promotional_notifications",
    }
    preference_field = preference_by_type.get(kind)
    if preference_field and not getattr(customer, preference_field, True):
        return None

    item = Notification(
        customer_id=customer.customer_id,
        title=str(title or "Bank Notification")[:150],
        message=str(message or "")[:5000],
        notification_type=(notification_type or "General")[:50],
        is_read=False,
    )
    db.session.add(item)
    if commit:
        db.session.commit()
    return item


class BankMessage(db.Model):
    __tablename__ = "bank_messages"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id"),
        nullable=False,
        index=True
    )

    subject = db.Column(
        db.String(200),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Unread"
    )

    sender_type = db.Column(
        db.String(20),
        nullable=False,
        default="customer"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class PaymentApproval(db.Model):
    __tablename__ = "payment_approvals"

    id = db.Column(db.Integer, primary_key=True)

    payment_reference = db.Column(
        db.String(40),
        unique=True,
        nullable=False,
        index=True
    )

    customer_id = db.Column(
        db.String(20),
        nullable=False,
        index=True
    )

    payment_type = db.Column(
        db.String(80),
        nullable=False
    )

    direction = db.Column(
        db.String(20),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    description = db.Column(
        db.String(255),
        nullable=False
    )

    counterparty = db.Column(
        db.String(150),
        nullable=True
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Pending Approval",
        index=True
    )

    sender_name = db.Column(
        db.String(150),
        nullable=True
    )

    sender_account_number = db.Column(
        db.String(50),
        nullable=True
    )

    sender_bank = db.Column(
        db.String(150),
        nullable=True
    )

    sender_country = db.Column(
        db.String(100),
        nullable=True
    )

    recipient_customer_id = db.Column(
        db.String(20),
        nullable=True
    )

    recipient_name = db.Column(
        db.String(150),
        nullable=True
    )

    recipient_email = db.Column(
    db.String(254),
    nullable=False,
    default=""

    )

    recipient_account_number = db.Column(
        db.String(50),
        nullable=True
    )

    original_transaction_reference = db.Column(
        db.String(40),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    reviewed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    reviewed_by = db.Column(
        db.String(80),
        nullable=True
    )

    rejection_reason = db.Column(
        db.String(500),
        nullable=True
    )

    tcc_status = db.Column(
        db.String(30),
        nullable=False,
        default="Not Required"
    )

    tcc_code = db.Column(
        db.String(6),
        nullable=True
    )

    tcc_generated_at = db.Column(
        db.DateTime,
        nullable=True
    )

    tcc_expires_at = db.Column(
        db.DateTime,
        nullable=True
    )

    tcc_verified_at = db.Column(
        db.DateTime,
        nullable=True
    )

    tcc_attempts = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )


# =========================================================
# VIRTUAL ATM CARD
# =========================================================
# Simulated local-app card record.
# This is not connected to a real card network.

class VirtualATMCard(db.Model):
    __tablename__ = "virtual_atm_cards"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.String(20),
        unique=True,
        nullable=False,
        index=True
    )

    card_number = db.Column(
        db.String(19),
        unique=True,
        nullable=False
    )

    expiry_date = db.Column(
        db.String(7),
        nullable=False
    )

    security_code = db.Column(
        db.String(3),
        nullable=True
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Active"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )


# =========================================================
# VIRTUAL ATM CARD APPLICATIONS
# =========================================================

class VirtualCardApplication(db.Model):
    __tablename__ = "virtual_card_applications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.String(20),
        unique=True,
        nullable=False,
        index=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Pending"
    )

    submitted_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    reviewed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    reviewed_by = db.Column(
        db.String(100),
        nullable=True
    )

    rejection_reason = db.Column(
        db.String(255),
        nullable=True
    )

# =========================================================


class Bank(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    country = db.Column(
        db.String(100),
        nullable=False,
        default="United Kingdom"
    )

    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )




class Recipient(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.String(20),
        nullable=False,
        index=True
    )

    recipient_name = db.Column(
        db.String(150),
        nullable=False
    )

    bank_name = db.Column(
        db.String(150),
        nullable=False
    )

    account_number = db.Column(
        db.String(40),
        nullable=False
    )

    sort_code = db.Column(
        db.String(20),
        nullable=True
    )

    country = db.Column(
        db.String(100),
        nullable=False,
        default="United Kingdom"
    )

    currency = db.Column(
        db.String(10),
        nullable=False,
        default="GBP"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )




class ExternalTransfer(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    transaction_reference = db.Column(
        db.String(40),
        unique=True,
        nullable=False
    )

    customer_id = db.Column(
        db.String(20),
        nullable=False,
        index=True
    )

    transfer_type = db.Column(
        db.String(30),
        nullable=False
    )

    bank_name = db.Column(
        db.String(150),
        nullable=False
    )

    recipient_name = db.Column(
        db.String(150),
        nullable=False
    )

    recipient_email = db.Column(
        db.String(254),
        nullable=False,
        default=""
    )

    account_number = db.Column(
        db.String(40),
        nullable=False
    )

    sort_code = db.Column(
        db.String(20),
        nullable=True
    )

    country = db.Column(
        db.String(100),
        nullable=False
    )

    currency = db.Column(
        db.String(10),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    fee = db.Column(
        db.Float,
        nullable=False,
        default=0.0
    )

    reference = db.Column(
        db.String(255),
        nullable=True
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )


# CUSTOMER ID GENERATOR
# =========================================================

def generate_customer_id():

    while True:

        numbers = "".join(
            secrets.choice(string.digits)
            for _ in range(8)
        )

        customer_id = "FB" + numbers

        existing = Customer.query.filter_by(
            customer_id=customer_id
        ).first()

        if existing is None:

            return customer_id




# =========================================================
# VIRTUAL ATM CARD GENERATORS
# =========================================================

def generate_virtual_card_number():
    """
    Generate a unique simulated 16-digit card identifier.
    The 9999 prefix identifies it as a local non-payment card.
    """
    while True:
        suffix = "".join(
            secrets.choice(string.digits)
            for _ in range(12)
        )
        card_number = "9999" + suffix

        if VirtualATMCard.query.filter_by(
            card_number=card_number
        ).first() is None:
            return card_number


def generate_virtual_card_expiry():
    now = datetime.utcnow()
    return f"{now.year + 3:04d}-{now.month:02d}"


def generate_virtual_card_security_code():
    """
    Generate a 3-digit security code for the local simulated
    virtual ATM card. This app is not connected to a real card
    network or payment processor.
    """
    return f"{secrets.randbelow(1000):03d}"


# =========================================================
# TRANSACTION REFERENCE GENERATOR
# =========================================================



def generate_account_number():

    while True:

        number = "".join(
            secrets.choice(string.digits)
            for _ in range(10)
        )

        existing = Customer.query.filter_by(
            account_number=number
        ).first()

        if existing is None:
            return number


def generate_transaction_reference():

    while True:

        reference = (
            "FT"
            + datetime.utcnow().strftime("%Y%m%d%H%M%S")
            + secrets.token_hex(3).upper()
        )

        existing_transaction = Transaction.query.filter_by(
            transaction_reference=reference
        ).first()

        existing_approval = PaymentApproval.query.filter_by(
            payment_reference=reference
        ).first()

        existing_external = ExternalTransfer.query.filter_by(
            transaction_reference=reference
        ).first()

        if (
            existing_transaction is None
            and existing_approval is None
            and existing_external is None
        ):
            return reference


# =========================================================
# HOME
# =========================================================



# --------------------------------------------------
# Dashboard template values
# --------------------------------------------------

@app.context_processor
def inject_dashboard_values():
    """
    Always provide dashboard.html with the values it needs.

    This does not modify the customer's database record.
    It only supplies template variables while rendering.
    """

    balance = 0.0

    try:
        if current_user.is_authenticated:

            # Primary account-balance field.
            if hasattr(current_user, "account_balance"):
                balance = getattr(
                    current_user,
                    "account_balance",
                    0
                ) or 0

            # Compatibility with applications that use
            # "balance" instead.
            elif hasattr(current_user, "balance"):
                balance = getattr(
                    current_user,
                    "balance",
                    0
                ) or 0

    except Exception:
        balance = 0.0

    try:
        balance = float(balance)
    except (TypeError, ValueError):
        balance = 0.0

    return {
        "display_balance": balance,
        "currency_symbol": app.config.get(
            "CURRENCY_SYMBOL",
            "£"
        )
    }


# ============================================================
# FROZEN CUSTOMER ACCOUNT PAYMENT GUARD
# ============================================================

FROZEN_ACCOUNT_PAYMENT_PATHS = {
    "/send-money",
    "/send-fairmont-money",
    "/international-transfer",
    "/pay-bills",
    "/electric-bills",
    "/airtime",
    "/data-bundles",
    "/tv-subscriptions",
    "/lifestyle",
    "/flights-travel",
    "/withdraw/paypal",
    "/withdraw/card",
    "/withdraw/bank",
    "/withdraw/wise",
    "/withdraw/cashapp",
    "/withdraw/venmo",
    "/payment/tcc-verification",
}


@app.before_request
def enforce_frozen_customer_payment_block():
    """Prevent frozen customer accounts from submitting payment actions."""

    if request.path.startswith("/admin"):
        return None

    customer_id = session.get("customer_id")

    if not customer_id:
        return None

    path = request.path.rstrip("/") or "/"

    is_payment_path = (
        path in FROZEN_ACCOUNT_PAYMENT_PATHS
        or path.startswith("/withdraw/")
        or path.startswith("/payment/tcc-verification/")
    )

    if not is_payment_path:
        return None

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:
        return None

    if str(customer.account_status or "").strip().lower() == "locked":
        session["account_frozen_popup"] = True
        return redirect(url_for("dashboard"))

    return None


@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# CUSTOMER LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        customer_id = request.form.get(
            "customer_id",
            ""
        ).strip().upper()

        password = request.form.get(
            "password",
            ""
        )

        customer = Customer.query.filter_by(
            customer_id=customer_id
        ).first()

        if customer is None:

            return render_template(
                "login.html",
                error="Invalid Customer ID or password."
            )

        # A locked/frozen customer may still sign in and view the
        # account. Financial actions are blocked separately by the
        # frozen-account payment guard.
        if customer.account_status not in ("Active", "Locked"):

            return render_template(
                "login.html",
                error="Your account is currently unavailable. Please contact Fairmont Bank."
            )

        if not check_password_hash(
            customer.password_hash,
            password
        ):

            return render_template(
                "login.html",
                error="Invalid Customer ID or password."
            )

        # ADMIN CONTROLLED OTP LOGIN
        #
        # Only customers explicitly enabled by an administrator
        # require this additional verification step.

        if customer.login_otp_enabled:

            # Invalidate previous unused OTP codes.
            old_otps = (
                CustomerLoginOTP.query
                .filter_by(
                    customer_id=customer.id,
                    used=False
                )
                .all()
            )

            for old_otp in old_otps:
                old_otp.used = True

            # Generate a fresh six-digit OTP.
            otp_code = f"{secrets.randbelow(1000000):06d}"

            otp_record = CustomerLoginOTP(
                customer_id=customer.id,
                otp_code=otp_code,
                used=False,
                expires_at=(
                    datetime.now(timezone.utc)
                    + timedelta(minutes=10)
                ),
                created_at=datetime.now(timezone.utc)
            )

            db.session.add(otp_record)
            db.session.commit()

            session["pending_login_customer_id"] = customer.customer_id

            return render_template(
                "login_otp_verify.html",
                customer=customer,
                error=None
            )

        login_user(customer)

        session["customer_id"] = customer.customer_id

        next_url = request.form.get("next") or request.args.get("next")

        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)

        return redirect("/dashboard")

        login_user(customer)

        session["customer_id"] = customer.customer_id

        next_url = request.form.get("next") or request.args.get("next")

        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)

        return redirect("/dashboard")

    return render_template(
        "login.html"
    )





@app.route("/login/resend-otp", methods=["POST"])
def resend_login_otp():

    customer_id = session.get("pending_login_customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:
        session.pop("pending_login_customer_id", None)
        return redirect(url_for("login"))

    # OTP must still be controlled by the administrator.
    if not customer.login_otp_enabled:
        session.pop("pending_login_customer_id", None)
        return redirect(url_for("login"))

    # Invalidate all previous unused OTP codes.
    old_otps = (
        CustomerLoginOTP.query
        .filter_by(
            customer_id=customer.id,
            used=False
        )
        .all()
    )

    for old_otp in old_otps:
        old_otp.used = True

    # Generate a fresh six-digit OTP.
    otp_code = f"{secrets.randbelow(1000000):06d}"

    now_utc = datetime.now(timezone.utc)

    otp_record = CustomerLoginOTP(
        customer_id=customer.id,
        otp_code=otp_code,
        used=False,
        created_at=now_utc,
        expires_at=now_utc + timedelta(minutes=10)
    )

    db.session.add(otp_record)
    db.session.commit()

    return render_template(
        "login_otp_verify.html",
        customer=customer,
        error=None,
        message="A new verification code has been requested. Please contact Fairmont Bank support for your code."
    )


@app.route("/login/verify-otp", methods=["POST"])
def verify_login_otp():

    customer_id = session.get("pending_login_customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:
        session.pop("pending_login_customer_id", None)
        return redirect(url_for("login"))

    if not customer.login_otp_enabled:
        login_user(customer)
        session["customer_id"] = customer.customer_id
        session.pop("pending_login_customer_id", None)
        return redirect("/dashboard")

    entered_otp = request.form.get(
        "otp",
        ""
    ).strip()

    otp_record = (
        CustomerLoginOTP.query
        .filter_by(
            customer_id=customer.id,
            used=False
        )
        .order_by(
            CustomerLoginOTP.created_at.desc()
        )
        .first()
    )

    if otp_record is None:
        return render_template(
            "login_otp_verify.html",
            customer=customer,
            error="No active verification code is available. Please contact the bank administrator."
        )

    if otp_record.expires_at:
        expiry = otp_record.expires_at

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expiry:

            otp_record.used = True
            db.session.commit()

            return render_template(
                "login_otp_verify.html",
                customer=customer,
                error="This verification code has expired. Please contact the bank administrator for a new login attempt."
            )

    if entered_otp != otp_record.otp_code:

        return render_template(
            "login_otp_verify.html",
            customer=customer,
            error="Invalid verification code. Please contact the bank administrator."
        )

    otp_record.used = True

    login_user(customer)

    session["customer_id"] = customer.customer_id
    session.pop("pending_login_customer_id", None)

    db.session.commit()

    return redirect("/dashboard")


# =========================================================
# OPEN ACCOUNT
# =========================================================

@app.route("/open-account", methods=["GET", "POST"])
def open_account():

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        account_type = request.form.get(
            "account_type",
            ""
        ).strip()

        country = request.form.get(
            "country",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        terms = request.form.get(
            "terms"
        )

        if not all([
            full_name,
            email,
            phone,
            account_type,
            country,
            password
        ]):

            return (
                "Please complete all required fields.",
                400
            )

        if not terms:

            return (
                "You must accept the account terms.",
                400
            )

        existing_email = Customer.query.filter_by(
            email=email
        ).first()

        if existing_email:

            return (
                "An account with this email address already exists.",
                400
            )

        existing_phone = Customer.query.filter_by(
            phone=phone
        ).first()

        if existing_phone:

            return (
                "An account with this phone number already exists.",
                400
            )

        customer = Customer(

            customer_id=generate_customer_id(),

            account_number=generate_account_number(),

            full_name=full_name,

            email=email,

            phone=phone,

            account_type=account_type,

            country=country,

            password_hash=generate_password_hash(
                password
            ),

            account_status="Pending Approval",

            account_balance=0.0
        )

        db.session.add(customer)

        db.session.commit()

        account_email_text = f"""FAIRMONT BANK — ACCOUNT SERVICES

WE'VE RECEIVED YOUR ACCOUNT APPLICATION

Dear {customer.full_name},

Thank you for submitting your account application. The details below are provided for your reference.

APPLICATION DETAILS
Application Reference: {customer.customer_id}
Account Type: {customer.account_type}
Application Status: {customer.account_status}

WHAT HAPPENS NEXT?
Your application is awaiting review. Please check your account dashboard for status updates. Any additional steps will be communicated through the appropriate channels.

NEED ASSISTANCE?
Contact support@fairmontbank.com if you have questions about your application.

Kind regards,
Fairmont Bank
Account Services"""

        account_email_html = render_template(
            "emails/account_application_received.html",
            customer=customer
        )

        email_sent = send_bank_email(
            customer.email,
            "We've Received Your Account Application",
            account_email_text,
            html_body=account_email_html
        )
        if not email_sent:
            app.logger.warning(
                "Account application email could not be sent for customer %s",
                customer.customer_id,
            )

        return render_template(
            "account_created.html",
            customer=customer
        )

    return render_template(
        "open_account.html"
    )


# =========================================================
# LOGOUT
# =========================================================





# =========================================================
# TRANSACTION HISTORY
# =========================================================





@app.route("/settings/notification-preferences", methods=["GET", "POST"])
@login_required
def notification_preferences():
    customer = current_user

    if request.method == "POST":
        customer.transaction_notifications = (
            request.form.get("transaction_notifications") == "on"
        )

        customer.security_notifications = (
            request.form.get("security_notifications") == "on"
        )

        customer.account_notifications = (
            request.form.get("account_notifications") == "on"
        )

        customer.promotional_notifications = (
            request.form.get("promotional_notifications") == "on"
        )

        db.session.commit()

        return redirect(url_for("notification_preferences"))

    return render_template(
        "notification_preferences.html",
        customer=customer
    )


@app.route("/notifications")
def notifications():

    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:
        session.clear()
        return redirect(url_for("login"))

    notification_list = (
        Notification.query
        .filter_by(customer_id=customer.customer_id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    unread_count = (
        Notification.query
        .filter_by(
            customer_id=customer.customer_id,
            is_read=False
        )
        .count()
    )

    return render_template(
        "notifications.html",
        customer=customer,
        notifications=notification_list,
        unread_count=unread_count
    )


@app.route("/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):

    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    notification = Notification.query.filter_by(
        id=notification_id,
        customer_id=customer_id
    ).first()

    if notification is None:
        return ("Notification not found.", 404)

    notification.is_read = True

    db.session.commit()

    return redirect(url_for("notifications"))


@app.route("/notifications/mark-all-read", methods=["POST"])
def mark_all_notifications_read():

    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    Notification.query.filter_by(
        customer_id=customer_id,
        is_read=False
    ).update(
        {
            "is_read": True
        },
        synchronize_session=False
    )

    db.session.commit()

    return redirect(url_for("notifications"))



# =========================================================
# ADMIN: SITE NOTIFICATIONS
# =========================================================

@app.route("/admin/notifications", methods=["GET", "POST"])
def admin_notifications():
    admin_id = session.get("admin_id")
    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)
    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    customers = Customer.query.order_by(Customer.full_name.asc()).all()
    error = None
    success = None

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        notification_type = request.form.get("notification_type", "General").strip()
        audience = request.form.get("audience", "all").strip()
        selected_customer_id = request.form.get("customer_id", "").strip()

        allowed_types = {"General", "Transaction", "Security", "Account", "Promotional"}
        if notification_type not in allowed_types:
            notification_type = "General"

        if not title or not message:
            error = "Enter both a notification title and message."
        elif audience == "one" and not selected_customer_id:
            error = "Choose a customer for a targeted notification."
        else:
            if audience == "one":
                recipients = Customer.query.filter_by(
                    customer_id=selected_customer_id
                ).all()
            else:
                recipients = customers

            if not recipients:
                error = "No matching customer was found."
            else:
                created_count = 0
                for recipient in recipients:
                    item = create_customer_notification(
                        recipient.customer_id,
                        title,
                        message,
                        notification_type=notification_type,
                        commit=False,
                    )
                    if item is not None:
                        created_count += 1

                if created_count:
                    db.session.commit()
                    success = f"Notification sent to {created_count} customer(s)."
                else:
                    db.session.rollback()
                    error = (
                        "No notification was sent. The selected customers may "
                        "have disabled this notification category."
                    )

    recent_notifications = Notification.query.order_by(
        Notification.created_at.desc()
    ).limit(30).all()

    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Site Notifications | Fairmont Bank Admin</title>
      <style>
        *{box-sizing:border-box}body{margin:0;background:#f3f6fb;color:#172033;
        font-family:Arial,sans-serif}.wrap{max-width:1100px;margin:32px auto;padding:0 18px}
        .top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
        h1{margin:0 0 8px;color:#142b4a}.muted{color:#68758a}
        .card{background:white;border:1px solid #e1e7ef;border-radius:14px;padding:22px;
        margin:20px 0;box-shadow:0 5px 18px #1720330b}
        label{display:block;font-weight:700;margin:14px 0 6px}
        input,textarea,select{width:100%;padding:12px;border:1px solid #cbd5e1;
        border-radius:8px;font:inherit}textarea{min-height:120px;resize:vertical}
        button,.btn{display:inline-block;border:0;border-radius:8px;background:#173b66;
        color:white;padding:12px 17px;font-weight:700;cursor:pointer;text-decoration:none}
        .btn.secondary{background:#e8eef6;color:#173b66}
        .msg{padding:12px 14px;border-radius:8px;margin:14px 0}
        .ok{background:#e8f8ef;color:#17663b}.err{background:#fff0f0;color:#9d2525}
        .row{display:grid;grid-template-columns:1fr 1fr;gap:14px}
        .notice{padding:14px 0;border-bottom:1px solid #e7ebf2}
        .notice:last-child{border-bottom:0}.pill{font-size:12px;background:#edf2f8;
        padding:4px 8px;border-radius:99px}.unread{font-weight:700}
        @media(max-width:650px){.row{grid-template-columns:1fr}.card{padding:16px}}
      </style>
    </head>
    <body><main class="wrap">
      <div class="top">
        <div><h1>Site Notifications</h1>
        <div class="muted">Signed in as {{ admin.username }} · Send in-site messages to customers.</div></div>
        <a class="btn secondary" href="{{ url_for('admin_dashboard') }}">Back to Admin Dashboard</a>
      </div>
      {% if success %}<div class="msg ok">{{ success }}</div>{% endif %}
      {% if error %}<div class="msg err">{{ error }}</div>{% endif %}
      <section class="card">
        <h2>Compose notification</h2>
        <form method="post">
          <div class="row">
            <div><label for="title">Title</label>
              <input id="title" name="title" maxlength="150" required></div>
            <div><label for="notification_type">Category</label>
              <select id="notification_type" name="notification_type">
                <option>General</option><option>Account</option><option>Transaction</option>
                <option>Security</option><option>Promotional</option>
              </select></div>
          </div>
          <label for="message">Message</label>
          <textarea id="message" name="message" maxlength="5000" required></textarea>
          <label for="audience">Recipients</label>
          <select id="audience" name="audience" onchange="document.getElementById('customer-wrap').style.display=this.value==='one'?'block':'none'">
            <option value="all">All customers (respecting notification preferences)</option>
            <option value="one">One customer</option>
          </select>
          <div id="customer-wrap" style="display:none">
            <label for="customer_id">Customer</label>
            <select id="customer_id" name="customer_id">
              <option value="">Select customer</option>
              {% for c in customers %}
                <option value="{{ c.customer_id }}">{{ c.full_name }} — {{ c.customer_id }}</option>
              {% endfor %}
            </select>
          </div>
          <p><button type="submit">Send Notification</button></p>
        </form>
      </section>
      <section class="card">
        <h2>Recent notifications</h2>
        {% for n in recent_notifications %}
          <div class="notice">
            <div><strong>{{ n.title }}</strong> <span class="pill">{{ n.notification_type }}</span>
            {% if not n.is_read %}<span class="pill">Unread</span>{% endif %}</div>
            <p>{{ n.message }}</p>
            <div class="muted">Customer ID: {{ n.customer_id }} ·
              {{ n.created_at.strftime('%d %b %Y, %H:%M') if n.created_at else '' }}</div>
          </div>
        {% else %}<p class="muted">No notifications have been created yet.</p>{% endfor %}
      </section>
    </main></body></html>
    """, admin=admin, customers=customers,
        recent_notifications=recent_notifications,
        error=error, success=success)




@app.route("/transactions")
def transactions():

    customer_id = session.get("customer_id")

    if not customer_id:

        return render_template(
            "login.html",
            error="Please sign in to view your transactions."
        )

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:

        session.clear()

        return render_template(
            "login.html",
            error="Your session could not be verified. Please sign in again."
        )

    search = request.args.get("search", "").strip()
    transaction_type = request.args.get("type", "").strip()
    direction = request.args.get("direction", "").strip()
    date_range = request.args.get("date_range", "").strip()

    query = Transaction.query.filter_by(
        customer_id=customer.customer_id
    )

    if search:
        search_value = f"%{search}%"

        query = query.filter(
            db.or_(
                Transaction.description.ilike(search_value),
                Transaction.counterparty.ilike(search_value),
                Transaction.transaction_reference.ilike(search_value)
            )
        )

    if transaction_type:
        query = query.filter(
            Transaction.transaction_type == transaction_type
        )

    if direction in ("Credit", "Debit"):
        query = query.filter(
            Transaction.direction == direction
        )

    if date_range in ("today", "7", "30"):

        from datetime import timedelta

        now = datetime.now()

        if date_range == "today":
            start_date = now.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )

        elif date_range == "7":
            start_date = now - timedelta(days=7)

        else:
            start_date = now - timedelta(days=30)

        query = query.filter(
            Transaction.created_at >= start_date
        )

    transaction_list = (
        query
        .order_by(Transaction.created_at.desc())
        .all()
    )

    transaction_types = (
        db.session.query(Transaction.transaction_type)
        .filter_by(customer_id=customer.customer_id)
        .distinct()
        .order_by(Transaction.transaction_type.asc())
        .all()
    )

    transaction_types = [
        item[0]
        for item in transaction_types
        if item[0]
    ]

    return render_template(
        "transactions.html",
        customer=customer,
        transactions=transaction_list,
        transaction_types=transaction_types,
        search=search,
        selected_type=transaction_type,
        selected_direction=direction,
        selected_date_range=date_range
    )




# =========================================================
# TRANSACTION DETAILS
# =========================================================

@app.route("/transaction/<transaction_reference>")
def transaction_details(transaction_reference):

    customer_id = session.get("customer_id")

    if not customer_id:

        return render_template(
            "login.html",
            error="Please sign in to view this transaction."
        )

    transaction = Transaction.query.filter_by(
        transaction_reference=transaction_reference,
        customer_id=customer_id
    ).first()

    if transaction is None:

        return (
            "Transaction not found.",
            404
        )

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    return render_template(
        "transaction_details.html",
        customer=customer,
        transaction=transaction
    )


# =========================================================
# MY PROFILE
# =========================================================



# =========================================================
# ACCOUNT PREFERENCE DATABASE MIGRATION
# =========================================================

def ensure_account_preference_columns():

    inspector = db.inspect(db.engine)

    columns = [
        column["name"]
        for column in inspector.get_columns("customer")
    ]

    migrations = {
        "preferred_language":
            "VARCHAR(20) NOT NULL DEFAULT 'English'",

        "preferred_currency_display":
            "VARCHAR(10) NOT NULL DEFAULT 'GBP'",

        "preferred_date_format":
            "VARCHAR(30) NOT NULL DEFAULT 'DD/MM/YYYY'",

        "account_display_preference":
            "VARCHAR(30) NOT NULL DEFAULT 'Standard'"
    }

    for column_name, definition in migrations.items():

        if column_name not in columns:

            with db.engine.begin() as connection:

                connection.exec_driver_sql(
                    f"""
                    ALTER TABLE customer
                    ADD COLUMN {column_name}
                    {definition}
                    """
                )


# =========================================================
# VIRTUAL CARD SECURITY-CODE DATABASE MIGRATION
# =========================================================

def ensure_virtual_card_security_code_column():
    """
    Add the security_code column to existing Fairmont databases
    without deleting customer or card records. Existing cards that
    do not have a code receive a newly generated 3-digit code.
    """

    inspector = db.inspect(db.engine)

    if not inspector.has_table("virtual_atm_cards"):
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("virtual_atm_cards")
    }

    if "security_code" not in columns:
        with db.engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE virtual_atm_cards "
                "ADD COLUMN security_code VARCHAR(3)"
            )

    cards_without_code = (
        VirtualATMCard.query
        .filter(
            db.or_(
                VirtualATMCard.security_code.is_(None),
                VirtualATMCard.security_code == ""
            )
        )
        .all()
    )

    if cards_without_code:
        for card in cards_without_code:
            card.security_code = generate_virtual_card_security_code()

        db.session.commit()


# =========================================================
# CUSTOMER DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    customer_id = session.get("customer_id")

    if not customer_id:

        return render_template(
            "login.html",
            error="Please sign in to access your dashboard.",
        )

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:

        session.clear()

        return render_template(
            "login.html",
            error="Your session could not be verified. Please sign in again."
        )

    notification_unread_count = (
        Notification.query
        .filter_by(
            customer_id=customer.customer_id,
            is_read=False
        )
        .count()
    )

    # ---------------------------------------------------------
    # RECENT ACTIVITIES
    # ---------------------------------------------------------
    #
    # Load the customer's newest completed/recorded transactions.
    # Payment approvals are also included so newly submitted
    # payments can appear in Recent Activities before management
    # approval.
    #

    recent_transactions = (
        Transaction.query
        .filter(
            db.or_(
                Transaction.customer_id == customer.customer_id,
                Transaction.customer_id == str(customer.id)
            )
        )
        .order_by(
            Transaction.created_at.desc()
        )
        .limit(5)
        .all()
    )

    recent_payment_approvals = (
        PaymentApproval.query
        .filter_by(
            customer_id=customer.customer_id
        )
        .order_by(
            PaymentApproval.created_at.desc()
        )
        .limit(5)
        .all()
    )

    recent_activities = []

    for transaction in recent_transactions:
        recent_activities.append({
            "source": "transaction",
            "created_at": transaction.created_at,
            "transaction": transaction,
            "approval": None
        })

    for approval in recent_payment_approvals:
        recent_activities.append({
            "source": "payment",
            "created_at": approval.created_at,
            "transaction": None,
            "approval": approval
        })

    recent_activities.sort(
        key=lambda item: item["created_at"],
        reverse=True
    )

    recent_activities = recent_activities[:8]

    virtual_card = VirtualATMCard.query.filter_by(
        customer_id=customer.customer_id
    ).first()
    virtual_card_application = VirtualCardApplication.query.filter_by(
        customer_id=customer.customer_id
    ).first()

    # DASHBOARD BALANCE REPAIR
    # Always provide the real customer account balance
    # to dashboard.html.
    display_balance = customer.account_balance or 0
    return render_template(
        "dashboard.html",
        customer=customer,
        notification_unread_count=notification_unread_count,
        recent_transactions=recent_transactions,
        virtual_card=virtual_card,
        virtual_card_application=virtual_card_application,
        display_balance=display_balance,
        currency_symbol=app.config.get("CURRENCY_SYMBOL", "£"),
        currency_locale=app.config.get("CURRENCY_LOCALE", "en-GB"),
    )

# =========================================================
# CUSTOMER VIRTUAL ATM CARD
# =========================================================
@app.route("/virtual-card/details")
@login_required
def virtual_card_details():
    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    card = VirtualATMCard.query.filter_by(
        customer_id=customer_id
    ).first()

    if card is None:
        flash("No virtual ATM card was found.", "error")
        return redirect(url_for("dashboard"))

    return render_template(
        "virtual_card_details.html",
        virtual_card=card
    )
@app.route("/virtual-card/apply", methods=["POST"])
@login_required
def apply_virtual_card():
    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:
        session.clear()
        return redirect(url_for("login"))

    existing_card = VirtualATMCard.query.filter_by(
        customer_id=customer.customer_id
    ).first()

    # An active or frozen card cannot have a replacement application.
    # A cancelled card may be replaced, but only after admin approval.
    if existing_card is not None and existing_card.status != "Cancelled":
        flash("You already have a virtual ATM card.", "info")
        return redirect(url_for("dashboard"))

    application = VirtualCardApplication.query.filter_by(
        customer_id=customer.customer_id
    ).first()

    if application is not None:
        if application.status == "Pending":
            flash(
                "Your virtual ATM card application is awaiting "
                "administrator approval.",
                "info"
            )
            return redirect(url_for("dashboard"))

        if application.status == "Approved" and existing_card is not None:
            # An approved application with a cancelled card can be
            # resubmitted as a replacement request.
            if existing_card.status != "Cancelled":
                flash(
                    "Your application has already been approved.",
                    "info"
                )
                return redirect(url_for("dashboard"))

        # Reuse the customer's unique application record.
        application.status = "Pending"
        application.submitted_at = datetime.utcnow()
        application.reviewed_at = None
        application.reviewed_by = None
        application.rejection_reason = None
    else:
        application = VirtualCardApplication(
            customer_id=customer.customer_id,
            status="Pending"
        )
        db.session.add(application)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(
            "Your application could not be submitted. "
            "Please try again.",
            "error"
        )
        return redirect(url_for("dashboard"))

    create_customer_notification(
        customer.customer_id,
        "Virtual card application received",
        "Your virtual ATM card application has been received and is awaiting administrator review.",
        notification_type="Account",
    )

    flash(
        "Your replacement virtual ATM card application has been submitted. "
        "Please wait for administrator approval.",
        "success"
    )
    return redirect(url_for("dashboard"))


# =========================================================
# CUSTOMER — MY PROFILE
# =========================================================

@app.route("/my-profile")
def my_profile():

    if "customer_id" not in session:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=session["customer_id"]
    ).first()

    if customer is None:
        session.clear()
        return redirect(url_for("login"))

    return render_template(
        "my_profile.html",
        customer=customer
    )


# =========================================================
# VIRTUAL CARD MANAGEMENT
# =========================================================

@app.route("/virtual-card/freeze", methods=["POST"])
@login_required
def virtual_card_freeze():

    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    card = VirtualATMCard.query.filter_by(
        customer_id=customer_id
    ).first()

    if not card:
        flash("No virtual card was found.", "error")
        return redirect(url_for("dashboard"))

    if card.status == "Cancelled":
        flash("A cancelled card cannot be frozen.", "error")
        return redirect(url_for("virtual_card_details"))

    if card.status == "Frozen":
        flash("Your virtual card is already frozen.", "info")
        return redirect(url_for("virtual_card_details"))

    card.status = "Frozen"

    db.session.commit()

    flash("Your virtual card has been frozen.", "success")

    return redirect(url_for("virtual_card_details"))


@app.route("/virtual-card/unfreeze", methods=["POST"])
@login_required
def virtual_card_unfreeze():

    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    card = VirtualATMCard.query.filter_by(
        customer_id=customer_id
    ).first()

    if not card:
        flash("No virtual card was found.", "error")
        return redirect(url_for("dashboard"))

    if card.status == "Cancelled":
        flash("A cancelled card cannot be unfrozen.", "error")
        return redirect(url_for("virtual_card_details"))

    if card.status == "Active":
        flash("Your virtual card is already active.", "info")
        return redirect(url_for("virtual_card_details"))

    card.status = "Active"

    db.session.commit()

    flash(
        "Your virtual card has been unfrozen and is active again.",
        "success"
    )

    return redirect(url_for("virtual_card_details"))


@app.route("/virtual-card/cancel", methods=["POST"])
@login_required
def virtual_card_cancel():
    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    card = VirtualATMCard.query.filter_by(
        customer_id=customer_id
    ).first()

    if not card:
        flash("No virtual card was found.", "error")
        return redirect(url_for("dashboard"))

    if card.status == "Cancelled":
        flash("Your virtual card is already cancelled.", "info")
        return redirect(url_for("virtual_card_details"))

    card.status = "Cancelled"
    db.session.commit()

    flash(
        "Your virtual card has been cancelled. "
        "You may apply for a replacement card subject to administrator approval.",
        "success"
    )
    return redirect(url_for("virtual_card_details"))


@app.route("/logout")
def logout():

    session.clear()

    return render_template(
        "login.html"
    )


# =========================================================
# LIVE CHAT GUEST SESSION DATABASE MIGRATION
# =========================================================

def ensure_live_chat_guest_column():
    """Add guest_session_id to older live-chat tables if needed."""
    try:
        inspector = db.inspect(db.engine)

        if "live_chat_conversations" not in inspector.get_table_names():
            return

        columns = {
            column["name"]
            for column in inspector.get_columns(
                "live_chat_conversations"
            )
        }

        if "guest_session_id" not in columns:
            with db.engine.begin() as connection:
                connection.exec_driver_sql(
                    "ALTER TABLE live_chat_conversations "
                    "ADD COLUMN guest_session_id VARCHAR(120)"
                )

    except Exception as exc:
        print(
            "LIVE CHAT GUEST SESSION MIGRATION: skipped:",
            exc
        )


# =========================================================
# APPLICATION START
# =========================================================


# =========================================================
# SQLITE PAYMENT APPROVAL ID REPAIR
# =========================================================

def repair_payment_approvals_sequence():
    """
    Keeps SQLite's payment_approvals AUTOINCREMENT sequence
    synchronized with the highest existing payment_approvals.id.

    This is needed after importing or migrating database records,
    which can leave SQLite attempting to reuse an existing ID.
    """

    try:
        if not db.engine.url.drivername.startswith("sqlite"):
            return

        table_exists = db.session.execute(
            db.text("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'payment_approvals'
            """)
        ).scalar()

        if not table_exists:
            return

        max_id = db.session.execute(
            db.text("""
                SELECT COALESCE(MAX(id), 0)
                FROM payment_approvals
            """)
        ).scalar()

        sequence_exists = db.session.execute(
            db.text("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'sqlite_sequence'
            """)
        ).scalar()

        if not sequence_exists:
            return

        current_sequence = db.session.execute(
            db.text("""
                SELECT seq
                FROM sqlite_sequence
                WHERE name = 'payment_approvals'
            """)
        ).scalar()

        if current_sequence is None:
            db.session.execute(
                db.text("""
                    INSERT INTO sqlite_sequence (name, seq)
                    VALUES ('payment_approvals', :seq)
                """),
                {"seq": int(max_id)}
            )

        elif int(current_sequence) < int(max_id):
            db.session.execute(
                db.text("""
                    UPDATE sqlite_sequence
                    SET seq = :seq
                    WHERE name = 'payment_approvals'
                """),
                {"seq": int(max_id)}
            )

        db.session.commit()

    except Exception:
        db.session.rollback()


# ============================================================
# PAYMENT TCC VERIFICATION
# ============================================================

def generate_payment_tcc_code():
    """
    Generate a six-digit TCC for the local Fairmont
    payment-verification workflow.
    """

    return f"{secrets.randbelow(1000000):06d}"


def apply_tcc_requirement(customer, approval):
    """
    Apply the customer's TCC payment restriction to a
    newly created PaymentApproval.

    TCC OFF:
        Payment remains Pending Approval.

    TCC ON:
        A unique TCC is generated and the payment becomes
        TCC Verification Required.
    """

    if not getattr(
        customer,
        "tcc_payment_restriction_enabled",
        False
    ):

        approval.status = "Pending Approval"
        approval.tcc_status = "Not Required"
        approval.tcc_code = None
        approval.tcc_generated_at = None
        approval.tcc_expires_at = None
        approval.tcc_verified_at = None
        approval.tcc_attempts = 0

        return approval


    now = datetime.utcnow()

    approval.status = "TCC Verification Required"
    approval.tcc_status = "Required"

    approval.tcc_code = generate_payment_tcc_code()

    approval.tcc_generated_at = now

    approval.tcc_expires_at = (
        now + timedelta(minutes=15)
    )

    approval.tcc_verified_at = None

    approval.tcc_attempts = 0

    return approval

# =========================================================
# WITHDRAW MONEY
# =========================================================

@app.route("/withdraw", methods=["GET"])
def withdraw():

    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:
        session.clear()
        return redirect(url_for("login"))

    return render_template(
        "withdraw.html",
        customer=customer
    )


# =========================================================
# PAYPAL WITHDRAWAL REQUEST
# =========================================================

@app.route("/withdraw/paypal", methods=["GET", "POST"])
def withdraw_paypal():

    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":

        paypal_email = request.form.get(
            "paypal_email", ""
        ).strip().lower()

        amount_text = request.form.get(
            "amount", ""
        ).strip()

        if not paypal_email or "@" not in paypal_email:
            flash(
                "Please enter a valid PayPal email address.",
                "error"
            )
            return render_template(
                "withdraw_paypal.html",
                customer=customer
            )

        try:
            amount = float(amount_text)
        except (TypeError, ValueError):
            flash(
                "Please enter a valid withdrawal amount.",
                "error"
            )
            return render_template(
                "withdraw_paypal.html",
                customer=customer
            )

        if amount <= 0:
            flash(
                "Withdrawal amount must be greater than zero.",
                "error"
            )
            return render_template(
                "withdraw_paypal.html",
                customer=customer
            )

        available_balance = float(
            customer.account_balance or 0
        )

        if amount > available_balance:
            flash(
                "The withdrawal amount exceeds your available balance.",
                "error"
            )
            return render_template(
                "withdraw_paypal.html",
                customer=customer
            )

        # PaymentApproval.payment_reference is required by the
        # existing database, so generate one for every withdrawal.
        payment_reference = generate_transaction_reference()

        approval = PaymentApproval(
            payment_reference=payment_reference,
            customer_id=customer.customer_id,
            payment_type="PayPal Withdrawal",
            direction="Debit",
            amount=amount,
            description=f"PayPal withdrawal to {paypal_email}",
            counterparty=paypal_email,
            status="Pending Approval",
        )

        # Respect the same TCC/payment-restriction workflow used
        # by the other customer payment routes.
        apply_tcc_requirement(
            customer,
            approval
        )

        db.session.add(approval)
        db.session.commit()
        if not send_payment_status_email(customer, approval, event="submitted"):
            app.logger.warning(
                "Payment request email could not be sent for reference %s",
                approval.payment_reference,
            )

        if approval.status == "TCC Verification Required":
            return redirect(
                url_for(
                    "payment_tcc_verification",
                    approval_id=approval.id
                )
            )

        flash(
            "Your PayPal withdrawal request has been submitted successfully and is now pending review.",
            "success"
        )

        return redirect(url_for("withdraw"))

    return render_template(
        "withdraw_paypal.html",
        customer=customer
    )



# =========================================================
# DEBIT CARD WITHDRAWAL REQUEST
# =========================================================

@app.route("/withdraw/card", methods=["GET", "POST"])
def withdraw_card():

    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":

        cardholder_name = request.form.get(
            "cardholder_name",
            ""
        ).strip()

        card_number = request.form.get(
            "card_number",
            ""
        ).replace(" ", "").replace("-", "").strip()

        expiry_month = request.form.get(
            "expiry_month",
            ""
        ).strip()

        expiry_year = request.form.get(
            "expiry_year",
            ""
        ).strip()

        amount_text = request.form.get(
            "amount",
            ""
        ).strip()

        if not cardholder_name:
            flash(
                "Please enter the cardholder name.",
                "error"
            )
            return render_template(
                "withdraw_card.html",
                customer=customer
            )

        if not card_number.isdigit() or not (12 <= len(card_number) <= 19):
            flash(
                "Please enter a valid debit card number.",
                "error"
            )
            return render_template(
                "withdraw_card.html",
                customer=customer
            )

        if not expiry_month or not expiry_year:
            flash(
                "Please enter the card expiry date.",
                "error"
            )
            return render_template(
                "withdraw_card.html",
                customer=customer
            )

        try:
            amount = float(amount_text)
        except (TypeError, ValueError):
            flash(
                "Please enter a valid withdrawal amount.",
                "error"
            )
            return render_template(
                "withdraw_card.html",
                customer=customer
            )

        if amount <= 0:
            flash(
                "Withdrawal amount must be greater than zero.",
                "error"
            )
            return render_template(
                "withdraw_card.html",
                customer=customer
            )

        available_balance = float(
            customer.account_balance or 0
        )

        if amount > available_balance:
            flash(
                "The withdrawal amount exceeds your available balance.",
                "error"
            )
            return render_template(
                "withdraw_card.html",
                customer=customer
            )

        # Never store the full card number, CVV, or other sensitive
        # card credentials in the bank database.
        masked_card = "**** **** **** " + card_number[-4:]

        payment_reference = generate_transaction_reference()

        approval = PaymentApproval(
            payment_reference=payment_reference,
            customer_id=customer.customer_id,
            payment_type="Debit Card Withdrawal",
            direction="Debit",
            amount=amount,
            description=(
                f"Debit card withdrawal to {masked_card} "
                f"(Expiry: {expiry_month}/{expiry_year})"
            ),
            counterparty=cardholder_name,
            status="Pending Approval",
        )

        apply_tcc_requirement(
            customer,
            approval
        )

        db.session.add(approval)
        db.session.commit()
        if not send_payment_status_email(customer, approval, event="submitted"):
            app.logger.warning(
                "Payment request email could not be sent for reference %s",
                approval.payment_reference,
            )

        if approval.status == "TCC Verification Required":
            return redirect(
                url_for(
                    "payment_tcc_verification",
                    approval_id=approval.id
                )
            )

        flash(
            "Your debit card withdrawal request has been submitted successfully and is now pending review.",
            "success"
        )

        return redirect(url_for("withdraw"))

    return render_template(
        "withdraw_card.html",
        customer=customer
    )


# =========================================================
# BANK ACCOUNT WITHDRAWAL REQUEST
# =========================================================

@app.route("/withdraw/bank", methods=["GET", "POST"])
def withdraw_bank():

    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":

        account_holder_name = request.form.get(
            "account_holder_name",
            ""
        ).strip()

        bank_name = request.form.get(
            "bank_name",
            ""
        ).strip()

        account_number = request.form.get(
            "account_number",
            ""
        ).strip()

        sort_code = request.form.get(
            "sort_code",
            ""
        ).strip()

        amount_text = request.form.get(
            "amount",
            ""
        ).strip()

        reference = request.form.get(
            "reference",
            ""
        ).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not account_holder_name:
            flash(
                "Please enter the account holder name.",
                "error"
            )
            return render_template(
                "withdraw_bank.html",
                customer=customer
            )

        if not bank_name:
            flash(
                "Please enter the bank name.",
                "error"
            )
            return render_template(
                "withdraw_bank.html",
                customer=customer
            )

        if not account_number:
            flash(
                "Please enter the bank account number.",
                "error"
            )
            return render_template(
                "withdraw_bank.html",
                customer=customer
            )

        if not sort_code:
            flash(
                "Please enter the sort code or routing number.",
                "error"
            )
            return render_template(
                "withdraw_bank.html",
                customer=customer
            )

        try:
            amount = float(amount_text)
        except (TypeError, ValueError):
            flash(
                "Please enter a valid withdrawal amount.",
                "error"
            )
            return render_template(
                "withdraw_bank.html",
                customer=customer
            )

        if amount <= 0:
            flash(
                "Withdrawal amount must be greater than zero.",
                "error"
            )
            return render_template(
                "withdraw_bank.html",
                customer=customer
            )

        available_balance = float(
            customer.account_balance or 0
        )

        if amount > available_balance:
            flash(
                "The withdrawal amount exceeds your available balance.",
                "error"
            )
            return render_template(
                "withdraw_bank.html",
                customer=customer
            )

        # Keep the full bank details only in the approval record
        # required by the existing application workflow. Never ask
        # customers for online-banking passwords, PINs, or security codes.
        payment_reference = generate_transaction_reference()

        account_suffix = account_number[-4:] if len(account_number) >= 4 else account_number

        description = (
            f"Bank account withdrawal to {account_holder_name} - "
            f"{bank_name} - Account ending {account_suffix}"
        )

        if reference:
            description += f" - Ref: {reference}"

        approval = PaymentApproval(
            payment_reference=payment_reference,
            customer_id=customer.customer_id,
            payment_type="Bank Account Withdrawal",
            direction="Debit",
            amount=amount,
            description=description,
            counterparty=account_holder_name,
            status="Pending Approval",
            sender_name=customer.full_name,
            sender_account_number=customer.account_number,
            sender_bank="Fairmont Bank",
            sender_country=customer.country,
            recipient_name=account_holder_name,
            recipient_account_number=account_number,
        )

        apply_tcc_requirement(
            customer,
            approval
        )

        db.session.add(approval)
        db.session.commit()
        if not send_payment_status_email(customer, approval, event="submitted"):
            app.logger.warning(
                "Payment request email could not be sent for reference %s",
                approval.payment_reference,
            )

        if approval.status == "TCC Verification Required":
            return redirect(
                url_for(
                    "payment_tcc_verification",
                    approval_id=approval.id
                )
            )

        flash(
            "Your bank account withdrawal request has been submitted successfully and is now pending review.",
            "success"
        )

        return redirect(url_for("withdraw"))

    return render_template(
        "withdraw_bank.html",
        customer=customer
    )

# =========================================================
# WISE / CASH APP / VENMO WITHDRAWAL REQUESTS
# =========================================================

_EXTERNAL_WITHDRAWAL_TEMPLATE = r"""
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{{ method }} Withdrawal</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f4f7fb;color:#182230}.wrap{max-width:720px;margin:0 auto;padding:28px 18px 50px}.back{display:inline-block;margin-bottom:20px;color:#40556f;text-decoration:none;font-weight:600}.card{background:#fff;border:1px solid #e3e9f1;border-radius:20px;box-shadow:0 10px 30px rgba(20,40,70,.08);overflow:hidden}.head{padding:28px 28px 22px;border-bottom:1px solid #edf1f5}.icon{width:52px;height:52px;border-radius:14px;display:flex;align-items:center;justify-content:center;background:#eef5ff;color:#2367c8;font-size:25px;margin-bottom:14px}h1{margin:0 0 8px;font-size:26px}.sub{margin:0;color:#66758a;line-height:1.5}.body{padding:28px}.balance{padding:15px 16px;margin-bottom:22px;background:#f7f9fc;border:1px solid #e7edf4;border-radius:12px}.balance span{display:block;color:#718096;font-size:13px;margin-bottom:4px}.balance strong{font-size:21px}label{display:block;font-size:14px;font-weight:700;margin:17px 0 7px}input{width:100%;padding:13px 14px;border:1px solid #cfd8e3;border-radius:10px;font-size:15px;outline:none}input:focus{border-color:#3779d3;box-shadow:0 0 0 3px rgba(55,121,211,.10)}button{width:100%;margin-top:24px;padding:14px 18px;border:0;border-radius:11px;background:#2367c8;color:white;font-size:15px;font-weight:700;cursor:pointer}.flash{margin-bottom:16px;padding:13px 14px;border-radius:10px;font-size:14px}.flash.error{background:#fff1f1;color:#a12626;border:1px solid #f2cccc}.flash.success{background:#effaf3;color:#176b3a;border:1px solid #ccebd7}.notice{margin-top:17px;padding:13px 14px;border-radius:10px;background:#f8fafc;color:#66758a;font-size:12px;line-height:1.5}@media(max-width:560px){.body,.head{padding:22px}}
</style></head><body><div class="wrap"><a class="back" href="{{ url_for('withdraw') }}">← Back to withdrawal methods</a><div class="card"><div class="head"><div class="icon">{{ icon }}</div><h1>Withdraw to {{ method }}</h1><p class="sub">Enter your {{ field_label|lower }} and withdrawal amount.</p></div><div class="body">{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for category, message in messages %}<div class="flash {{ category }}">{{ message }}</div>{% endfor %}{% endif %}{% endwith %}<div class="balance"><span>Available balance</span><strong>£{{ "%.2f"|format(customer.account_balance or 0) }}</strong></div><form method="POST" action="{{ action_url }}"><label for="destination">{{ field_label }}</label><input id="destination" name="destination" type="text" value="{{ request.form.get('destination','') }}" required><label for="amount">Withdrawal amount</label><input id="amount" name="amount" type="number" min="0.01" step="0.01" value="{{ request.form.get('amount','') }}" inputmode="decimal" required><button type="submit">Submit Withdrawal Request</button></form><div class="notice">Your request is submitted for review. A pending request does not reduce the account balance until it is approved by the authorized bank administrator.</div></div></div></div></body></html>
"""

def _external_withdrawal_page(method, field_label, payment_type, icon, endpoint):
    customer_id = session.get("customer_id")
    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(customer_id=customer_id).first()
    if customer is None:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":
        destination = request.form.get("destination", "").strip()
        amount_text = request.form.get("amount", "").strip()
        if not destination:
            flash(f"Please enter your {field_label.lower()}.", "error")
            return redirect(url_for(endpoint))
        try:
            amount = float(amount_text)
        except (TypeError, ValueError):
            flash("Please enter a valid withdrawal amount.", "error")
            return redirect(url_for(endpoint))
        if amount <= 0:
            flash("Withdrawal amount must be greater than zero.", "error")
            return redirect(url_for(endpoint))
        if amount > float(customer.account_balance or 0):
            flash("The withdrawal amount exceeds your available balance.", "error")
            return redirect(url_for(endpoint))
        approval = PaymentApproval(
            payment_reference=generate_transaction_reference(),
            customer_id=customer.customer_id,
            payment_type=payment_type,
            direction="Debit",
            amount=amount,
            description=f"{method} withdrawal to {destination}",
            counterparty=destination,
            status="Pending Approval",
        )
        apply_tcc_requirement(customer, approval)
        db.session.add(approval)
        db.session.commit()
        if not send_payment_status_email(customer, approval, event="submitted"):
            app.logger.warning(
                "Payment request email could not be sent for reference %s",
                approval.payment_reference,
            )
        if approval.status == "TCC Verification Required":
            return redirect(url_for("payment_tcc_verification", approval_id=approval.id))
        flash(f"Your {method} withdrawal request has been submitted successfully and is now pending review.", "success")
        return redirect(url_for("withdraw"))

    return render_template_string(_EXTERNAL_WITHDRAWAL_TEMPLATE, customer=customer, method=method, field_label=field_label, icon=icon, action_url=url_for(endpoint))


@app.route("/withdraw/wise", methods=["GET", "POST"])
def withdraw_wise():
    return _external_withdrawal_page("Wise", "Wise email or account ID", "Wise Withdrawal", "W", "withdraw_wise")


@app.route("/withdraw/cashapp", methods=["GET", "POST"])
def withdraw_cashapp():
    return _external_withdrawal_page("Cash App", "Cash App $Cashtag", "Cash App Withdrawal", "$", "withdraw_cashapp")


@app.route("/withdraw/venmo", methods=["GET", "POST"])
def withdraw_venmo():
    return _external_withdrawal_page("Venmo", "Venmo username", "Venmo Withdrawal", "V", "withdraw_venmo")



# =========================================================
# SEND MONEY TO ANOTHER FAIRMONT BANK CUSTOMER
# =========================================================

@app.route("/send-fairmont-money", methods=["GET", "POST"])
def send_fairmont_money():

    if "customer_id" not in session:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=session["customer_id"]
    ).first()

    if customer is None:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "send_fairmont_money.html",
            customer=customer
        )

    recipient_account_number = request.form.get(
        "recipient_account_number",
        ""
    ).strip()

    amount_text = request.form.get(
        "amount",
        ""
    ).strip()

    reference = request.form.get(
        "reference",
        ""
    ).strip()

    if not re.fullmatch(
        r"\d{10}",
        recipient_account_number
    ):
        flash(
            "Fairmont account number must contain exactly 10 digits.",
            "error"
        )
        return redirect(url_for("send_fairmont_money"))

    try:
        amount = float(amount_text)
    except (TypeError, ValueError):
        flash(
            "Please enter a valid amount.",
            "error"
        )
        return redirect(url_for("send_fairmont_money"))

    if amount <= 0:
        flash(
            "Transfer amount must be greater than zero.",
            "error"
        )
        return redirect(url_for("send_fairmont_money"))

    sender_balance = float(
        customer.account_balance or 0
    )

    if amount > sender_balance:
        flash(
            "Insufficient available balance.",
            "error"
        )
        return redirect(url_for("send_fairmont_money"))

    recipient = Customer.query.filter_by(
        account_number=recipient_account_number
    ).first()

    if recipient is None:
        flash(
            "No Fairmont customer was found with that account number.",
            "error"
        )
        return redirect(url_for("send_fairmont_money"))

    if recipient.id == customer.id:
        flash(
            "You cannot send money to your own account.",
            "error"
        )
        return redirect(url_for("send_fairmont_money"))

    if str(
        recipient.account_status
    ).lower() != "active":
        flash(
            "The recipient account is not active.",
            "error"
        )
        return redirect(url_for("send_fairmont_money"))

    previous_sender_balance = float(
        customer.account_balance or 0
    )

    previous_recipient_balance = float(
        recipient.account_balance or 0
    )

    new_sender_balance = (
        previous_sender_balance - amount
    )

    new_recipient_balance = (
        previous_recipient_balance + amount
    )

    sender_transaction_reference = (
        generate_transaction_reference()
    )

    recipient_transaction_reference = (
        generate_transaction_reference()
    )

    # The database requires transaction_reference to be unique.
    # Make absolutely sure the two references are different.
    while recipient_transaction_reference == sender_transaction_reference:
        recipient_transaction_reference = (
            generate_transaction_reference()
        )

    sender_transaction = Transaction(
        transaction_reference=sender_transaction_reference,
        customer_id=customer.customer_id,
        transaction_type="Fairmont Internal Transfer",
        direction="Debit",
        amount=amount,
        balance_after=new_sender_balance,
        description=(
            reference
            or f"Transfer to {recipient.full_name}"
        ),
        counterparty=recipient.full_name,
        status="Completed",
        sender_name=customer.full_name,
        sender_account_number=customer.account_number,
        sender_bank="Fairmont Bank",
        sender_country=customer.country
    )

    recipient_transaction = Transaction(
        transaction_reference=recipient_transaction_reference,
        customer_id=recipient.customer_id,
        transaction_type="Fairmont Internal Transfer",
        direction="Credit",
        amount=amount,
        balance_after=new_recipient_balance,
        description=(
            f"Transfer from {customer.full_name}"
        ),
        counterparty=customer.full_name,
        status="Completed",
        sender_name=customer.full_name,
        sender_account_number=customer.account_number,
        sender_bank="Fairmont Bank",
        sender_country=customer.country
    )

    customer.account_balance = new_sender_balance
    recipient.account_balance = new_recipient_balance

    db.session.add(sender_transaction)
    db.session.add(recipient_transaction)

    create_customer_notification(
        customer.customer_id,
        "Money transfer sent",
        f"Your transfer of £{amount:,.2f} to {recipient.full_name} was completed successfully. Reference: {sender_transaction_reference}.",
        notification_type="Transaction",
        commit=False,
    )
    create_customer_notification(
        recipient.customer_id,
        "Money received",
        f"You received £{amount:,.2f} from {customer.full_name}. Reference: {recipient_transaction_reference}.",
        notification_type="Transaction",
        commit=False,
    )

    try:
        db.session.commit()

    except Exception as e:
        db.session.rollback()

        print("=" * 70)
        print(" FAIRMONT TRANSFER DATABASE ERROR")
        print("=" * 70)
        print()
        print("Exception type:", type(e).__name__)
        print("Exception message:", str(e))
        print()
        print("FULL DATABASE ERROR:")
        print(repr(e))
        print("=" * 70)

        flash(
            "Transfer failed. Check the server console for the database error.",
            "error"
        )

        return redirect(url_for("send_fairmont_money"))

    # Send debit/credit alerts only after both balance changes and
    # transaction records have been committed successfully.
    if not send_transaction_alert(customer, sender_transaction):
        app.logger.info(
            "Sender transaction alert not sent for reference %s",
            sender_transaction_reference,
        )
    if not send_transaction_alert(recipient, recipient_transaction):
        app.logger.info(
            "Recipient transaction alert not sent for reference %s",
            recipient_transaction_reference,
        )

    return render_template(
        "send_fairmont_money_success.html",
        customer=customer,
        recipient=recipient,
        amount=amount,
        previous_sender_balance=previous_sender_balance,
        new_sender_balance=new_sender_balance,
        previous_recipient_balance=previous_recipient_balance,
        new_recipient_balance=new_recipient_balance,
        reference=reference,
        transaction_reference=sender_transaction_reference
    )


@app.route("/send-money", methods=["GET", "POST"])
def send_money():

    repair_payment_approvals_sequence()


    if "customer_id" not in session:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=session["customer_id"]
    ).first()

    if not customer:
        session.clear()
        return redirect(url_for("login"))

    banks = Bank.query.filter_by(
        country="United Kingdom",
        active=True
    ).order_by(Bank.name.asc()).all()

    if request.method == "GET":
        return render_template(
            "send_money.html",
            customer=customer,
            banks=banks
        )

    recipient_name = request.form.get(
        "recipient_name",
        ""
    ).strip()

    bank_name = request.form.get(
        "bank_name",
        ""
    ).strip()

    account_number = request.form.get(
        "account_number",
        ""
    ).strip()

    sort_code = request.form.get(
        "sort_code",
        ""
    ).strip()

    reference = request.form.get(
        "reference",
        ""
    ).strip()

    amount_text = request.form.get(
        "amount",
        ""
    ).strip()

    if not recipient_name:
        flash(
            "Please enter the recipient name.",
            "error"
        )
        return redirect(url_for("send_money"))

    if not bank_name:
        flash(
            "Please select a bank.",
            "error"
        )
        return redirect(url_for("send_money"))

    if not re.fullmatch(r"\d{8}", account_number):
        flash(
            "Account number must contain exactly 10 digits.",
            "error"
        )
        return redirect(url_for("send_money"))

    if not re.fullmatch(r"\d{6}", sort_code):
        flash(
            "Sort code must contain exactly 6 digits.",
            "error"
        )
        return redirect(url_for("send_money"))

    try:
        amount = float(amount_text)
    except (TypeError, ValueError):
        flash(
            "Please enter a valid amount.",
            "error"
        )
        return redirect(url_for("send_money"))

    if amount <= 0:
        flash(
            "Payment amount must be greater than zero.",
            "error"
        )
        return redirect(url_for("send_money"))

    if amount > float(customer.account_balance or 0):
        flash(
            "Insufficient available balance.",
            "error"
        )
        return redirect(url_for("send_money"))

    recipient_customer = Customer.query.filter_by(
        account_number=account_number
    ).first()

    if (
        recipient_customer
        and recipient_customer.customer_id == customer.customer_id
    ):
        flash(
            "You cannot send a payment to your own account.",
            "error"
        )
        return redirect(url_for("send_money"))

    payment_reference = generate_transaction_reference()

    # ---------------------------------------------------------
    # INTERNAL FAIRMONT CUSTOMER PAYMENT
    # ---------------------------------------------------------

    if recipient_customer:

        if str(
            recipient_customer.account_status
        ).lower() != "active":

            flash(
                "The recipient account is not active.",
                "error"
            )
            return redirect(url_for("send_money"))

        approval = PaymentApproval(
            payment_reference=payment_reference,
            customer_id=customer.customer_id,
            payment_type="Bank Transfer",
            direction="Debit",
            amount=amount,
            description=reference or "Bank payment",
            counterparty=recipient_customer.full_name,
            status="Pending Approval",
            recipient_customer_id=recipient_customer.customer_id,
            recipient_name=recipient_customer.full_name,
            recipient_account_number=recipient_customer.account_number,
            sender_name=customer.full_name,
            sender_account_number=customer.account_number,
            sender_bank="Fairmont Bank",
            sender_country=customer.country,
        )

        apply_tcc_requirement(
            customer,
            approval
        )
        db.session.add(approval)

        try:
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            # Repair a possible SQLite primary-key sequence mismatch.
            repair_payment_approvals_sequence()

            # Try the insert again.
            db.session.add(approval)
            db.session.commit()

        if not send_payment_status_email(customer, approval, event="submitted"):
            app.logger.warning(
                "Payment request email could not be sent for reference %s",
                approval.payment_reference,
            )

        if approval.status == "TCC Verification Required":

            return redirect(
                url_for(
                    "payment_tcc_verification",
                    approval_id=approval.id
                )
            )

        return render_template(
            "payment_pending_confirmation.html",
            customer=customer,
            approval=approval,
            amount=amount,
            recipient_name=recipient_customer.full_name,
            bank_name=bank_name,
            account_number=account_number,
            sort_code=sort_code,
            reference=reference,
        )

    # ---------------------------------------------------------
    # EXTERNAL UK BANK PAYMENT
    # ---------------------------------------------------------

    approval = PaymentApproval(
        payment_reference=payment_reference,
        customer_id=customer.customer_id,
        payment_type="UK Bank Payment",
        direction="Debit",
        amount=amount,
        description=reference or "UK Bank payment",
        counterparty=recipient_name,
        status="Pending Approval",
        recipient_name=recipient_name,
        recipient_account_number=account_number,
        sender_name=customer.full_name,
        sender_account_number=customer.account_number,
        sender_bank="Fairmont Bank",
        sender_country=customer.country,
    )

    # UK bank payments do not require a TCC code.
    # They remain pending for the normal payment-approval workflow.
    approval.status = "Pending Approval"
    approval.tcc_status = "Not Required"
    approval.tcc_code = None
    approval.tcc_generated_at = None
    approval.tcc_expires_at = None
    approval.tcc_verified_at = None
    approval.tcc_attempts = 0

    db.session.add(approval)
    db.session.commit()
    if not send_payment_status_email(customer, approval, event="submitted"):
        app.logger.warning(
            "Payment request email could not be sent for reference %s",
            approval.payment_reference,
        )

    return render_template(
        "payment_pending_confirmation.html",
        customer=customer,
        approval=approval,
        amount=amount,
        recipient_name=recipient_name,
        bank_name=bank_name,
        account_number=account_number,
        sort_code=sort_code,
        reference=reference,
    )


@app.route("/international-transfer", methods=["GET", "POST"])
@login_required
def international_transfer():
    """Create an international transfer request for administrator approval.

    The request is recorded in both ExternalTransfer and PaymentApproval so
    it appears in the existing Payment Approvals screen. The customer's
    balance is not changed until an administrator approves the request.
    """

    customer = current_user

    if request.method == "GET":
        return render_template(
            "international_transfer.html",
            customer=customer
        )

    country = request.form.get("country", "").strip()
    recipient_name = request.form.get("recipient_name", "").strip()
    recipient_email = request.form.get("recipient_email", "").strip().lower()
    recipient_address = request.form.get("recipient_address", "").strip()
    bank_name = request.form.get("bank_name", "").strip()
    account_number = request.form.get("account_number", "").strip()
    swift_bic = request.form.get("swift_bic", "").strip()
    local_bank_code = request.form.get("local_bank_code", "").strip()
    currency = request.form.get("currency", "").strip().upper()
    amount_text = request.form.get("amount", "").strip()
    reference = request.form.get("reference", "").strip()

    if not all([
        country,
        recipient_name,
        recipient_address,
        recipient_email,
        bank_name,
        account_number,
        swift_bic,
        currency,
        amount_text
    ]):
        flash(
            "Please complete all required international transfer fields.",
            "error"
        )
        return render_template(
            "international_transfer.html",
            customer=customer
        )
    if (
        len(recipient_email) > 254
        or "@" not in recipient_email
        or recipient_email.startswith("@")
        or recipient_email.endswith("@")
        or "." not in recipient_email.rsplit("@", 1)[-1]
    ):
        flash(
            "Please enter a valid recipient email address.",
            "error"
        )
        return render_template(
            "international_transfer.html",
            customer=customer
        )

    try:
        amount = float(amount_text)
    except (TypeError, ValueError):
        flash("Please enter a valid transfer amount.", "error")
        return render_template(
            "international_transfer.html",
            customer=customer
        )

    if amount <= 0:
        flash("Transfer amount must be greater than zero.", "error")
        return render_template(
            "international_transfer.html",
            customer=customer
        )

    current_balance = float(customer.account_balance or 0)

    if amount > current_balance:
        flash(
            "The transfer amount exceeds your available balance.",
            "error"
        )
        return render_template(
            "international_transfer.html",
            customer=customer
        )

    transaction_reference = generate_transaction_reference()

    # Keep the existing ExternalTransfer record for transfer-specific
    # information. It remains Pending until the administrator reviews it.
    transfer = ExternalTransfer(
        transaction_reference=transaction_reference,
        customer_id=customer.customer_id,
        transfer_type="International Transfer",
        bank_name=bank_name,
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        account_number=account_number,
        sort_code=local_bank_code or None,
        country=country,
        currency=currency,
        amount=amount,
        fee=0.0,
        reference=reference or "International Transfer",
        status="Pending"
    )

    # PaymentApproval is what the administration Payment Approvals page
    # already displays. Store the international request there as well.
    approval = PaymentApproval(
        payment_reference=transaction_reference,
        customer_id=customer.customer_id,
        payment_type="International Transfer",
        direction="Debit",
        amount=amount,
        description=(
            f"International transfer to {recipient_name} - "
            f"{bank_name}, {country}, {currency} "
            f"- Account: {account_number}"
            + (f" - SWIFT/BIC: {swift_bic}" if swift_bic else "")
            + (f" - Address: {recipient_address}" if recipient_address else "")
            + (f" - Bank code: {local_bank_code}" if local_bank_code else "")
            + (f" - Ref: {reference}" if reference else "")
        ),
        counterparty=recipient_name,
        status="Pending Approval",
        recipient_name=recipient_name,
        recipient_account_number=account_number,
        original_transaction_reference=transaction_reference
    )

    # Enforce the customer's existing TCC restriction before the
    # international transfer can reach the normal confirmation page.
    apply_tcc_requirement(
        customer,
        approval
    )

    # Keep the transfer record synchronized with the approval state.
    if approval.status == "TCC Verification Required":
        transfer.status = "TCC Verification Required"

    try:
        db.session.add(transfer)
        db.session.add(approval)
        db.session.commit()

        # 1. Notify the customer who submitted the transfer.
        if not send_payment_status_email(
            customer, approval, event="submitted"
        ):
            app.logger.warning(
                "Payment request email could not be sent for reference %s",
                approval.payment_reference,
            )

        # 2. Send the recipient a branded pending-status notification.
        if transfer.recipient_email:
            pending_email_sent = send_branded_recipient_email(
                recipient_email=transfer.recipient_email,
                recipient_name=transfer.recipient_name,
                subject="International Transfer Pending Approval",
                eyebrow="International Transfer",
                heading="International Transfer Pending Approval",
                message_text=(
                    "An international transfer request has been submitted "
                    "with you listed as the recipient.\n\n"
                    "The request is awaiting review. This notification does "
                    "not confirm that funds have been sent or credited to "
                    "your account. You will receive another notification "
                    "when the request status changes."
                ),
                details=[
                    ("Transfer type", "International Transfer"),
                    ("Amount", f"{transfer.amount:,.2f} {transfer.currency}"),
                    ("Reference", transfer.transaction_reference),
                    ("Sending bank", transfer.bank_name),
                    ("Country", transfer.country),
                    ("Status", "Pending Approval"),
                ],
            )
            if not pending_email_sent:
                app.logger.warning(
                    "Pending recipient email failed for reference %s",
                    transfer.transaction_reference,
                )

        # When TCC is enabled, do not show the normal submitted page.
        # Send the customer to the existing TCC verification workflow.
        if approval.status == "TCC Verification Required":
            return redirect(
                url_for(
                    "payment_tcc_verification",
                    approval_id=approval.id
                )
            )

    except IntegrityError:
        db.session.rollback()
        flash(
            "The transfer could not be submitted because its reference already exists. Please try again.",
            "error"
        )
        return render_template(
            "international_transfer.html",
            customer=customer
        )

    return render_template(
        "international_confirmation.html",
        customer=customer,
        transfer=transfer,
        transfer_reference=transaction_reference,
        approval=approval
    )


# ============================================================
# SERVICES HUB
# ============================================================


@app.route("/pay-bills", methods=["GET", "POST"])
@login_required

def pay_bills():

    customer = current_user

    if request.method == "GET":
        return render_template(
            "pay_bills.html",
            customer=customer
        )

    bill_category = request.form.get(
        "bill_category",
        ""
    ).strip()

    provider = request.form.get(
        "provider",
        ""
    ).strip()

    account_reference = request.form.get(
        "account_reference",
        ""
    ).strip()

    amount_text = request.form.get(
        "amount",
        ""
    ).strip()

    payment_reference = request.form.get(
        "payment_reference",
        ""
    ).strip()

    errors = []

    allowed_categories = {
        "Electricity",
        "Gas",
        "Water",
        "Council Tax",
        "Broadband",
        "Mobile Phone",
        "Landline",
        "TV & Entertainment",
        "Other Bills"
    }

    if bill_category not in allowed_categories:
        errors.append(
            "Please select a valid bill category."
        )

    if not provider:
        errors.append(
            "Please enter or select the bill provider."
        )

    if not account_reference:
        errors.append(
            "Please enter your customer or account reference."
        )

    try:
        amount = float(amount_text)
    except (TypeError, ValueError):
        amount = 0
        errors.append(
            "Please enter a valid payment amount."
        )

    if amount <= 0:
        if "Please enter a valid payment amount." not in errors:
            errors.append(
                "Payment amount must be greater than Â£0.00."
            )

    if amount > float(customer.account_balance or 0):
        errors.append(
            "Insufficient available balance."
        )

    if errors:
        return render_template(
            "pay_bills.html",
            customer=customer,
            errors=errors,
            form=request.form
        )

    approval = PaymentApproval(
        payment_reference=generate_transaction_reference(),
        customer_id=customer.customer_id,
        payment_type="Bill Payment",
        direction="Debit",
        amount=amount,
        description=(
            f"{bill_category} payment - "
            f"Account: {account_reference}"
            + (
                f" - Ref: {payment_reference}"
                if payment_reference else ""
            )
        ),
        counterparty=provider,
        status="Pending Approval",
    )

    apply_tcc_requirement(
        customer,
        approval
    )

    db.session.add(approval)
    db.session.commit()
    if not send_payment_status_email(customer, approval, event="submitted"):
        app.logger.warning(
            "Payment request email could not be sent for reference %s",
            approval.payment_reference,
        )

    if approval.status == "TCC Verification Required":
        return redirect(
            url_for(
                "payment_tcc_verification",
                approval_id=approval.id
            )
        )

    return render_template(
        "payment_pending_confirmation.html",
        customer=customer,
        approval=approval,
        amount=amount,
        recipient_name=provider,
        bank_name="Bill Payment",
        account_number=account_reference,
        sort_code="",
        reference=payment_reference,
    )


@app.route("/electric-bills", methods=["GET", "POST"])
@login_required

def electric_bills():

    customer = current_user

    if request.method == "GET":
        return render_template(
            "electric_bills.html",
            customer=customer
        )

    provider = request.form.get(
        "provider",
        ""
    ).strip()

    meter_number = request.form.get(
        "meter_number",
        ""
    ).strip()

    amount_text = request.form.get(
        "amount",
        ""
    ).strip()

    payment_reference = request.form.get(
        "payment_reference",
        ""
    ).strip()

    errors = []

    if not provider:
        errors.append("Please enter the electricity provider.")

    if not meter_number:
        errors.append("Please enter the meter or account number.")

    try:
        amount = float(amount_text)
    except (TypeError, ValueError):
        amount = 0

    if amount <= 0:
        errors.append("Please enter a valid payment amount.")

    if amount > float(customer.account_balance or 0):
        errors.append("Insufficient balance for this payment.")

    if errors:
        return render_template(
            "electric_bills.html",
            customer=customer,
            errors=errors,
            provider=provider,
            meter_number=meter_number,
            amount=amount_text,
            payment_reference=payment_reference
        )

    approval = PaymentApproval(
        payment_reference=generate_transaction_reference(),
        customer_id=customer.customer_id,
        payment_type="Electricity Bill",
        direction="Debit",
        amount=amount,
        description=(
            f"Electricity bill payment - Meter: {meter_number}"
            + (
                f" - Ref: {payment_reference}"
                if payment_reference else ""
            )
        ),
        counterparty=provider,
        status="Pending Approval",
    )

    apply_tcc_requirement(
        customer,
        approval
    )

    db.session.add(approval)
    db.session.commit()
    if not send_payment_status_email(customer, approval, event="submitted"):
        app.logger.warning(
            "Payment request email could not be sent for reference %s",
            approval.payment_reference,
        )

    if approval.status == "TCC Verification Required":
        return redirect(
            url_for(
                "payment_tcc_verification",
                approval_id=approval.id
            )
        )

    return render_template(
        "payment_pending_confirmation.html",
        customer=customer,
        approval=approval,
        amount=amount,
        recipient_name=provider,
        bank_name="Electricity Bill",
        account_number=meter_number,
        sort_code="",
        reference=payment_reference,
    )


@app.route("/airtime", methods=["GET", "POST"])
@login_required

def airtime():

    customer = current_user

    if request.method == "GET":
        return render_template(
            "airtime.html",
            customer=customer
        )

    provider = request.form.get(
        "provider", ""
    ).strip()

    phone_number = request.form.get(
        "phone_number", ""
    ).strip()

    amount_text = request.form.get(
        "amount", ""
    ).strip()

    payment_reference = request.form.get(
        "payment_reference", ""
    ).strip()

    errors = []

    if not provider:
        errors.append("Please select a mobile network.")

    if not phone_number:
        errors.append("Please enter the mobile phone number.")

    try:
        amount = float(amount_text)
    except (TypeError, ValueError):
        amount = 0

    if amount <= 0:
        errors.append("Please enter a valid airtime amount.")

    if amount > float(customer.account_balance or 0):
        errors.append("Insufficient balance for this airtime purchase.")

    if errors:
        return render_template(
            "airtime.html",
            customer=customer,
            errors=errors,
            provider=provider,
            phone_number=phone_number,
            amount=amount_text,
            payment_reference=payment_reference
        )

    approval = PaymentApproval(
        payment_reference=generate_transaction_reference(),
        customer_id=customer.customer_id,
        payment_type="Airtime Purchase",
        direction="Debit",
        amount=amount,
        description=(
            f"Mobile airtime purchase - "
            f"Phone: {phone_number}"
            + (
                f" - Ref: {payment_reference}"
                if payment_reference else ""
            )
        ),
        counterparty=provider,
        status="Pending Approval",
    )

    apply_tcc_requirement(
        customer,
        approval
    )

    db.session.add(approval)
    db.session.commit()
    if not send_payment_status_email(customer, approval, event="submitted"):
        app.logger.warning(
            "Payment request email could not be sent for reference %s",
            approval.payment_reference,
        )

    if approval.status == "TCC Verification Required":
        return redirect(
            url_for(
                "payment_tcc_verification",
                approval_id=approval.id
            )
        )

    return render_template(
        "payment_pending_confirmation.html",
        customer=customer,
        approval=approval,
        amount=amount,
        recipient_name=provider,
        bank_name="Mobile Airtime",
        account_number=phone_number,
        sort_code="",
        reference=payment_reference,
    )


@app.route("/data-bundles", methods=["GET", "POST"])
@login_required

def data_bundles():

    customer = current_user

    networks = [
        "EE",
        "O2",
        "Vodafone",
        "Three UK",
        "Tesco Mobile",
        "giffgaff",
        "Lebara",
        "Lycamobile",
        "Other Mobile Network"
    ]

    bundles = [
        {"name": "500 MB", "amount": 2.00},
        {"name": "1 GB", "amount": 5.00},
        {"name": "2 GB", "amount": 8.00},
        {"name": "5 GB", "amount": 12.00},
        {"name": "10 GB", "amount": 18.00},
        {"name": "20 GB", "amount": 25.00},
        {"name": "30 GB", "amount": 30.00},
        {"name": "50 GB", "amount": 40.00},
    ]

    if request.method == "GET":
        return render_template(
            "data_bundles.html",
            customer=customer,
            networks=networks,
            bundles=bundles
        )

    provider = request.form.get(
        "provider", ""
    ).strip()

    phone_number = request.form.get(
        "phone_number", ""
    ).strip()

    bundle_name = request.form.get(
        "bundle_name", ""
    ).strip()

    payment_reference = request.form.get(
        "payment_reference", ""
    ).strip()

    errors = []

    if provider not in networks:
        errors.append("Please select a mobile network.")

    if not phone_number:
        errors.append("Please enter the mobile phone number.")

    selected_bundle = None

    for bundle in bundles:
        if bundle["name"] == bundle_name:
            selected_bundle = bundle
            break

    if selected_bundle is None:
        errors.append("Please select a valid data bundle.")

    amount = selected_bundle["amount"] if selected_bundle else 0.0

    if amount > float(customer.account_balance or 0):
        errors.append(
            "Insufficient balance for this data bundle purchase."
        )

    if errors:
        return render_template(
            "data_bundles.html",
            customer=customer,
            networks=networks,
            bundles=bundles,
            errors=errors,
            provider=provider,
            phone_number=phone_number,
            bundle_name=bundle_name,
            payment_reference=payment_reference
        )

    approval = PaymentApproval(
        payment_reference=generate_transaction_reference(),
        customer_id=customer.customer_id,
        payment_type="Data Bundle Purchase",
        direction="Debit",
        amount=amount,
        description=(
            f"{bundle_name} mobile data bundle - "
            f"Phone: {phone_number}"
            + (
                f" - Ref: {payment_reference}"
                if payment_reference else ""
            )
        ),
        counterparty=provider,
        status="Pending Approval",
    )

    apply_tcc_requirement(
        customer,
        approval
    )

    db.session.add(approval)
    db.session.commit()
    if not send_payment_status_email(customer, approval, event="submitted"):
        app.logger.warning(
            "Payment request email could not be sent for reference %s",
            approval.payment_reference,
        )

    if approval.status == "TCC Verification Required":
        return redirect(
            url_for(
                "payment_tcc_verification",
                approval_id=approval.id
            )
        )

    return render_template(
        "payment_pending_confirmation.html",
        customer=customer,
        approval=approval,
        amount=amount,
        recipient_name=provider,
        bank_name="Mobile Data",
        account_number=phone_number,
        sort_code="",
        reference=payment_reference,
    )


@app.route("/tv-subscriptions", methods=["GET", "POST"])
@login_required

def tv_subscriptions():

    customer = current_user

    providers = [
        "Sky",
        "Virgin Media",
        "NOW TV",
        "BT TV",
        "EE TV",
        "Other TV Provider"
    ]

    packages = {
        "Sky": [
            {"name": "Sky Entertainment", "amount": 26.00},
            {"name": "Sky Cinema", "amount": 13.00},
            {"name": "Sky Sports", "amount": 25.00},
        ],
        "Virgin Media": [
            {"name": "Mixit TV", "amount": 30.00},
            {"name": "Maxit TV", "amount": 50.00},
            {"name": "Sports TV", "amount": 25.00},
        ],
        "NOW TV": [
            {"name": "Entertainment Membership", "amount": 9.99},
            {"name": "Cinema Membership", "amount": 9.99},
            {"name": "Sports Membership", "amount": 34.99},
        ],
        "BT TV": [
            {"name": "Entertainment", "amount": 18.00},
            {"name": "Big Entertainment", "amount": 25.00},
            {"name": "Sports", "amount": 30.00},
        ],
        "EE TV": [
            {"name": "Entertainment", "amount": 20.00},
            {"name": "Sports", "amount": 30.00},
        ],
        "Other TV Provider": [
            {"name": "Standard Subscription", "amount": 20.00},
            {"name": "Premium Subscription", "amount": 35.00},
        ]
    }

    if request.method == "GET":
        return render_template(
            "tv_subscriptions.html",
            customer=customer,
            providers=providers,
            packages=packages
        )

    provider = request.form.get(
        "provider", ""
    ).strip()

    package_name = request.form.get(
        "package_name", ""
    ).strip()

    account_reference = request.form.get(
        "account_reference", ""
    ).strip()

    payment_reference = request.form.get(
        "payment_reference", ""
    ).strip()

    errors = []

    if provider not in providers:
        errors.append("Please select a TV provider.")

    if not account_reference:
        errors.append(
            "Please enter your TV account or customer number."
        )

    selected_package = None

    if provider in packages:
        for package in packages[provider]:
            if package["name"] == package_name:
                selected_package = package
                break

    if selected_package is None:
        errors.append(
            "Please select a valid TV subscription package."
        )

    amount = selected_package["amount"] if selected_package else 0.0

    if amount > float(customer.account_balance or 0):
        errors.append(
            "Insufficient balance for this TV subscription payment."
        )

    if errors:
        return render_template(
            "tv_subscriptions.html",
            customer=customer,
            providers=providers,
            packages=packages,
            errors=errors,
            provider=provider,
            package_name=package_name,
            account_reference=account_reference,
            payment_reference=payment_reference
        )

    approval = PaymentApproval(
        payment_reference=generate_transaction_reference(),
        customer_id=customer.customer_id,
        payment_type="TV Subscription",
        direction="Debit",
        amount=amount,
        description=(
            f"{provider} - {package_name} - "
            f"Account: {account_reference}"
            + (
                f" - Ref: {payment_reference}"
                if payment_reference else ""
            )
        ),
        counterparty=provider,
        status="Pending Approval",
    )

    apply_tcc_requirement(
        customer,
        approval
    )

    db.session.add(approval)
    db.session.commit()
    if not send_payment_status_email(customer, approval, event="submitted"):
        app.logger.warning(
            "Payment request email could not be sent for reference %s",
            approval.payment_reference,
        )

    if approval.status == "TCC Verification Required":
        return redirect(
            url_for(
                "payment_tcc_verification",
                approval_id=approval.id
            )
        )

    return render_template(
        "payment_pending_confirmation.html",
        customer=customer,
        approval=approval,
        amount=amount,
        recipient_name=provider,
        bank_name="TV Subscription",
        account_number=account_reference,
        sort_code="",
        reference=payment_reference,
    )

@app.route("/bank-statements")
@login_required
def bank_statements():
    customer = current_user

    transactions = (
        Transaction.query
        .filter_by(customer_id=customer.customer_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    return render_template(
        "bank_statements.html",
        customer=customer,
        transactions=transactions,
        statement_date=datetime.now()
    )


@app.route("/bank-statements/download.csv")
@login_required
def download_bank_statement_csv():
    """Download the signed-in customer's existing transaction records as CSV."""
    customer = current_user

    if customer.bank_statements_locked:
        flash("Statement downloads are currently unavailable for this account. Please contact support.", "warning")
        return redirect(url_for("bank_statements"))

    transactions = (
        Transaction.query
        .filter_by(customer_id=customer.customer_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "Date", "Transaction Reference", "Type", "Direction", "Description",
        "Counterparty", "Amount (GBP)", "Balance After (GBP)", "Status"
    ])

    for transaction in transactions:
        writer.writerow([
            transaction.created_at.strftime("%Y-%m-%d %H:%M:%S") if transaction.created_at else "",
            transaction.transaction_reference or "",
            transaction.transaction_type or "",
            transaction.direction or "",
            transaction.description or "",
            transaction.counterparty or "",
            f"{float(transaction.amount or 0):.2f}",
            f"{float(transaction.balance_after or 0):.2f}",
            transaction.status or "",
        ])

    filename = f"statement_{customer.customer_id}_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.route("/lifestyle", methods=["GET", "POST"])
@login_required

def lifestyle():

    customer = current_user

    lifestyle_categories = [
        "Restaurants & Dining",
        "Shopping",
        "Entertainment",
        "Fitness & Wellness",
        "Beauty & Personal Care",
        "Travel & Leisure",
        "Events & Tickets",
        "Other Lifestyle"
    ]

    if request.method == "GET":
        return render_template(
            "lifestyle.html",
            customer=customer,
            categories=lifestyle_categories
        )

    category = request.form.get(
        "category", ""
    ).strip()

    merchant = request.form.get(
        "merchant", ""
    ).strip()

    account_reference = request.form.get(
        "account_reference", ""
    ).strip()

    amount_text = request.form.get(
        "amount", ""
    ).strip()

    payment_reference = request.form.get(
        "payment_reference", ""
    ).strip()

    errors = []

    if category not in lifestyle_categories:
        errors.append("Please select a lifestyle category.")

    if not merchant:
        errors.append("Please enter the merchant or service name.")

    if not account_reference:
        errors.append(
            "Please enter the customer or order reference."
        )

    try:
        amount = float(amount_text)
    except (TypeError, ValueError):
        amount = 0

    if amount <= 0:
        errors.append("Please enter a valid payment amount.")

    if amount > float(customer.account_balance or 0):
        errors.append(
            "Insufficient balance for this lifestyle payment."
        )

    if errors:
        return render_template(
            "lifestyle.html",
            customer=customer,
            categories=lifestyle_categories,
            errors=errors,
            category=category,
            merchant=merchant,
            account_reference=account_reference,
            amount=amount_text,
            payment_reference=payment_reference
        )

    approval = PaymentApproval(
        payment_reference=generate_transaction_reference(),
        customer_id=customer.customer_id,
        payment_type="Lifestyle Payment",
        direction="Debit",
        amount=amount,
        description=(
            f"{category} payment - "
            f"Reference: {account_reference}"
            + (
                f" - Ref: {payment_reference}"
                if payment_reference else ""
            )
        ),
        counterparty=merchant,
        status="Pending Approval",
    )

    apply_tcc_requirement(
        customer,
        approval
    )

    db.session.add(approval)
    db.session.commit()
    if not send_payment_status_email(customer, approval, event="submitted"):
        app.logger.warning(
            "Payment request email could not be sent for reference %s",
            approval.payment_reference,
        )

    if approval.status == "TCC Verification Required":
        return redirect(
            url_for(
                "payment_tcc_verification",
                approval_id=approval.id
            )
        )

    return render_template(
        "payment_pending_confirmation.html",
        customer=customer,
        approval=approval,
        amount=amount,
        recipient_name=merchant,
        bank_name="Lifestyle Payment",
        account_number=account_reference,
        sort_code="",
        reference=payment_reference,
    )


@app.route("/flights-travel", methods=["GET", "POST"])
@login_required

def flights_travel():

    customer = current_user

    travel_categories = [
        "Flight Booking",
        "Hotel Booking",
        "Airport Transfer",
        "Travel Insurance",
        "Train & Rail",
        "Bus & Coach",
        "Car Rental",
        "Other Travel"
    ]

    if request.method == "GET":
        return render_template(
            "flights_travel.html",
            customer=customer,
            categories=travel_categories
        )

    category = request.form.get(
        "category", ""
    ).strip()

    provider = request.form.get(
        "provider", ""
    ).strip()

    traveler_name = request.form.get(
        "traveler_name", ""
    ).strip()

    booking_reference = request.form.get(
        "booking_reference", ""
    ).strip()

    amount_text = request.form.get(
        "amount", ""
    ).strip()

    payment_reference = request.form.get(
        "payment_reference", ""
    ).strip()

    errors = []

    if category not in travel_categories:
        errors.append("Please select a travel service.")

    if not provider:
        errors.append(
            "Please enter the airline, hotel, or travel provider."
        )

    if not traveler_name:
        errors.append("Please enter the traveler name.")

    if not booking_reference:
        errors.append(
            "Please enter the booking or travel reference."
        )

    try:
        amount = float(amount_text)
    except (TypeError, ValueError):
        amount = 0

    if amount <= 0:
        errors.append("Please enter a valid payment amount.")

    if amount > float(customer.account_balance or 0):
        errors.append(
            "Insufficient balance for this travel payment."
        )

    if errors:
        return render_template(
            "flights_travel.html",
            customer=customer,
            categories=travel_categories,
            errors=errors,
            category=category,
            provider=provider,
            traveler_name=traveler_name,
            booking_reference=booking_reference,
            amount=amount_text,
            payment_reference=payment_reference
        )

    approval = PaymentApproval(
        payment_reference=generate_transaction_reference(),
        customer_id=customer.customer_id,
        payment_type="Travel Payment",
        direction="Debit",
        amount=amount,
        description=(
            f"{category} payment - "
            f"Traveler: {traveler_name} - "
            f"Booking: {booking_reference}"
            + (
                f" - Ref: {payment_reference}"
                if payment_reference else ""
            )
        ),
        counterparty=provider,
        status="Pending Approval",
    )

    apply_tcc_requirement(
        customer,
        approval
    )

    db.session.add(approval)
    db.session.commit()
    if not send_payment_status_email(customer, approval, event="submitted"):
        app.logger.warning(
            "Payment request email could not be sent for reference %s",
            approval.payment_reference,
        )

    if approval.status == "TCC Verification Required":
        return redirect(
            url_for(
                "payment_tcc_verification",
                approval_id=approval.id
            )
        )

    return render_template(
        "payment_pending_confirmation.html",
        customer=customer,
        approval=approval,
        amount=amount,
        recipient_name=provider,
        bank_name="Travel Payment",
        account_number=booking_reference,
        sort_code="",
        reference=payment_reference,
    )

# ============================================================
# CUSTOMER â€” TCC PAYMENT VERIFICATION
# ============================================================

@app.route(
    "/payment/tcc-verification/<int:approval_id>",
    methods=["GET", "POST"]
)
def payment_tcc_verification(approval_id):

    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:
        session.clear()
        return redirect(url_for("login"))

    approval = db.session.get(
        PaymentApproval,
        approval_id
    )

    if approval is None:
        flash(
            "The payment verification request could not be found.",
            "error"
        )
        return redirect(url_for("dashboard"))

    if approval.customer_id != customer.customer_id:
        flash(
            "You are not authorized to verify this payment.",
            "error"
        )
        return redirect(url_for("dashboard"))

    if approval.status != "TCC Verification Required":

        if approval.status == "Pending Approval":

            flash(
                "This payment has already completed TCC verification "
                "and is awaiting management approval.",
                "success"
            )

        elif approval.status == "Approved":

            flash(
                "This payment has already been approved.",
                "success"
            )

        else:

            flash(
                "This payment is no longer awaiting TCC verification.",
                "error"
            )

        return redirect(url_for("dashboard"))


    # --------------------------------------------------------
    # CHECK EXPIRATION
    # --------------------------------------------------------

    now = datetime.utcnow()

    if (
        approval.tcc_expires_at
        and now > approval.tcc_expires_at
    ):

        approval.tcc_status = "Expired"

        approval.status = "Rejected"

        approval.rejection_reason = (
            "TCC verification code expired."
        )

        approval.reviewed_at = now

        db.session.commit()

        return render_template(
            "tcc_verification.html",
            customer=customer,
            approval=approval,
            expired=True,
            error=(
                "This TCC has expired. "
                "Please start a new payment request."
            )
        )


    # --------------------------------------------------------
    # PROCESS CUSTOMER TCC
    # --------------------------------------------------------

    error = None

    if request.method == "POST":

        submitted_code = request.form.get(
            "tcc_code",
            ""
        ).strip()

        if not submitted_code:

            error = (
                "Please enter the TCC verification code."
            )

        elif not submitted_code.isdigit():

            error = (
                "The TCC must contain six digits."
            )

        elif len(submitted_code) != 6:

            error = (
                "The TCC must contain exactly six digits."
            )

        else:

            approval.tcc_attempts = (
                int(approval.tcc_attempts or 0) + 1
            )


            # ------------------------------------------------
            # MAXIMUM ATTEMPTS
            # ------------------------------------------------

            if approval.tcc_attempts > 5:

                approval.tcc_status = "Failed"

                approval.status = "Rejected"

                approval.rejection_reason = (
                    "Maximum TCC verification attempts exceeded."
                )

                approval.reviewed_at = now

                db.session.commit()

                return render_template(
                    "tcc_verification.html",
                    customer=customer,
                    approval=approval,
                    expired=False,
                    error=(
                        "The maximum number of TCC attempts "
                        "has been reached. Please start a new "
                        "payment request."
                    )
                )


            # ------------------------------------------------
            # VERIFY CODE
            # ------------------------------------------------

            if submitted_code == approval.tcc_code:

                approval.tcc_status = "Verified"

                approval.tcc_verified_at = now

                approval.status = "Pending Approval"

                approval.tcc_code = None

                db.session.commit()

                return render_template(
                    "payment_pending_confirmation.html",
                    customer=customer,
                    approval=approval,
                    amount=approval.amount,
                    recipient_name=(
                        approval.recipient_name
                        or approval.counterparty
                        or ""
                    ),
                    bank_name=(
                        approval.sender_bank
                        or "Fairmont Bank"
                    ),
                    account_number=(
                        approval.recipient_account_number
                        or ""
                    ),
                    sort_code="",
                    reference=approval.description,
                )


            error = (
                "The TCC entered does not match the code "
                "provided by Fairmont Bank Support."
            )

            db.session.commit()


    return render_template(
        "tcc_verification.html",
        customer=customer,
        approval=approval,
        expired=False,
        error=error
    )



def email_bank():

    messages = (
        BankMessage.query
        .filter_by(customer_id=current_user.id)
        .order_by(BankMessage.created_at.desc())
        .all()
    )

    if request.method == "POST":

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()

        if not subject:

            return render_template(
                "email_bank.html",
                customer=current_user,
                messages=messages,
                error="Please enter a subject."
            )

        if not message:

            return render_template(
                "email_bank.html",
                customer=current_user,
                messages=messages,
                error="Please enter a message."
            )

        if len(subject) > 200:

            return render_template(
                "email_bank.html",
                customer=current_user,
                messages=messages,
                error="Subject must be 200 characters or fewer."
            )

        if len(message) > 5000:

            return render_template(
                "email_bank.html",
                customer=current_user,
                messages=messages,
                error="Message must be 5,000 characters or fewer."
            )

        bank_message = BankMessage(
            customer_id=current_user.id,
            subject=subject,
            message=message,
            status="Unread",
            created_at=datetime.utcnow()
        )

        db.session.add(bank_message)
        db.session.commit()

        flash(
            "Your message has been sent to Fairmont Bank."
        )

        return redirect(
            url_for("email_bank")
        )

    return render_template(
        "email_bank.html",
        customer=current_user,
        messages=messages,
        error=None
    )




@app.route("/settings")
@login_required
def settings():
    customer = current_user
    return render_template("settings.html", customer=customer)




# =========================================================
# SECURITY & SESSION SETTINGS
# =========================================================

@app.route("/settings/security-session")
@login_required
def security_session_settings():
    customer = current_user

    return render_template(
        "security_session_settings.html",
        customer=customer
    )

@app.route(
    "/settings/account-preferences",
    methods=["GET", "POST"]
)
@login_required
def account_preferences():

    customer = current_user

    if request.method == "POST":

        preferred_language = request.form.get(
            "preferred_language",
            "English"
        ).strip()

        preferred_currency_display = request.form.get(
            "preferred_currency_display",
            "GBP"
        ).strip().upper()

        preferred_date_format = request.form.get(
            "preferred_date_format",
            "DD/MM/YYYY"
        ).strip()

        account_display_preference = request.form.get(
            "account_display_preference",
            "Standard"
        ).strip()

        allowed_languages = {
            "English"
        }

        allowed_currencies = {
            "GBP",
            "USD",
            "EUR"
        }

        allowed_date_formats = {
            "DD/MM/YYYY",
            "MM/DD/YYYY",
            "YYYY-MM-DD"
        }

        allowed_display_preferences = {
            "Standard",
            "Compact"
        }

        if preferred_language not in allowed_languages:
            preferred_language = "English"

        if preferred_currency_display not in allowed_currencies:
            preferred_currency_display = "GBP"

        if preferred_date_format not in allowed_date_formats:
            preferred_date_format = "DD/MM/YYYY"

        if account_display_preference not in allowed_display_preferences:
            account_display_preference = "Standard"

        customer.preferred_language = preferred_language
        customer.preferred_currency_display = (
            preferred_currency_display
        )
        customer.preferred_date_format = (
            preferred_date_format
        )
        customer.account_display_preference = (
            account_display_preference
        )

        db.session.commit()

        flash(
            "Your account preferences have been saved.",
            "success"
        )

        return redirect(
            url_for("account_preferences")
        )

    return render_template(
        "account_preferences.html",
        customer=customer
    )



@app.route("/personal-information")
@login_required
def personal_information():
    customer = current_user
    return render_template(
        "personal_information.html",
        customer=customer
    )



@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():

    customer = current_user

    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # Verify current password
        if not check_password_hash(
            customer.password_hash,
            current_password
        ):
            flash(
                "Your current password is incorrect.",
                "error"
            )

            return render_template(
                "change_password.html",
                customer=customer
            )

        # Validate new password length
        if len(new_password) < 8:
            flash(
                "Your new password must contain at least 8 characters.",
                "error"
            )

            return render_template(
                "change_password.html",
                customer=customer
            )

        # Confirm new password
        if new_password != confirm_password:
            flash(
                "The new passwords do not match.",
                "error"
            )

            return render_template(
                "change_password.html",
                customer=customer
            )

        # Do not allow the same password
        if check_password_hash(
            customer.password_hash,
            new_password
        ):
            flash(
                "Your new password must be different from your current password.",
                "error"
            )

            return render_template(
                "change_password.html",
                customer=customer
            )

        # Save the new hashed password
        customer.password_hash = generate_password_hash(
            new_password
        )

        db.session.commit()

        flash(
            "Your password has been changed successfully.",
            "success"
        )

        return redirect(
            url_for("settings")
        )

    return render_template(
        "change_password.html",
        customer=customer
    )


# =========================================================
# LOGIN OTP DATABASE MIGRATION
# =========================================================

def ensure_login_otp_column():

    inspector = db.inspect(db.engine)

    tables = inspector.get_table_names()

    if "customer" not in tables:
        return

    columns = [
        column["name"]
        for column in inspector.get_columns("customer")
    ]

    if "login_otp_enabled" not in columns:

        with db.engine.begin() as connection:

            connection.exec_driver_sql(
                """
                ALTER TABLE customer
                ADD COLUMN login_otp_enabled
                BOOLEAN NOT NULL DEFAULT 0
                """
            )


# ============================================================
# FAIRmont BANK LIVE CHAT
# Customer Support Chat
# ============================================================

@app.route("/api/live-chat/message", methods=["POST"])
def api_live_chat_message():
    """
    Public Live Chat API used by the floating homepage widget.

    Signed-in customers are attached to their own customer account.
    Visitors who are not signed in are placed into a dedicated support
    visitor record and identified by a browser session token.
    """

    data = request.get_json(silent=True) or {}
    message_text = str(data.get("message", "")).strip()

    if not message_text:
        return jsonify({
            "ok": False,
            "message": "Please enter a message."
        }), 400

    if len(message_text) > 2000:
        message_text = message_text[:2000]

    guest_session_id = None

    if current_user.is_authenticated:
        customer_id = current_user.id

    else:
        # Keep the visitor's support conversation tied to this browser.
        guest_session_id = session.get("live_chat_guest_token")

        if not guest_session_id:
            guest_session_id = secrets.token_urlsafe(32)
            session["live_chat_guest_token"] = guest_session_id
            session.modified = True

        # Reuse one non-login support visitor record so the existing
        # admin Live Chat page can display the conversation normally.
        guest_customer = Customer.query.filter_by(
            customer_id="GUESTCHAT"
        ).first()

        if guest_customer is None:
            guest_customer = Customer(
                customer_id="GUESTCHAT",
                account_number=None,
                full_name="Website Visitor",
                email="guest-chat@local.invalid",
                phone="GUEST-CHAT",
                account_type="Support Visitor",
                country="Website",
                password_hash=generate_password_hash(
                    secrets.token_urlsafe(32)
                ),
                account_status="Guest",
                account_balance=0.0
            )
            db.session.add(guest_customer)
            db.session.flush()

        customer_id = guest_customer.id

    query = LiveChatConversation.query.filter_by(
        customer_id=customer_id,
        status="Open"
    )

    if guest_session_id:
        query = query.filter_by(
            guest_session_id=guest_session_id
        )

    conversation = (
        query
        .order_by(LiveChatConversation.updated_at.desc())
        .first()
    )

    if conversation is None:
        conversation = LiveChatConversation(
            customer_id=customer_id,
            guest_session_id=guest_session_id,
            status="Open",
            subject="Website Live Chat"
        )
        db.session.add(conversation)
        db.session.flush()

    customer_message = LiveChatMessage(
        conversation_id=conversation.id,
        sender_type="customer",
        sender_id=(
            current_user.id
            if current_user.is_authenticated
            else None
        ),
        message=message_text,
        is_read=False,
        created_at=datetime.utcnow()
    )

    conversation.updated_at = datetime.utcnow()
    db.session.add(customer_message)
    db.session.commit()

    return jsonify({
        "ok": True,
        "message": (
            "Message sent successfully. "
            "Your message has been delivered to Fairmont Bank Support."
        )
    })


@app.route("/live-chat", methods=["GET", "POST"])
def live_chat():
    """
    Fairmont Bank customer Live Chat.

    Logged-in customers use their existing bank customer conversation.
    Visitors who are not logged in can still open the Live Chat page
    without accessing current_user.id.
    """

    # ---------------------------------------------------------
    # LOGGED-IN CUSTOMER CHAT
    # ---------------------------------------------------------
    if current_user.is_authenticated:

        conversation = (
            LiveChatConversation.query
            .filter_by(
                customer_id=current_user.id,
                status="Open"
            )
            .order_by(LiveChatConversation.created_at.desc())
            .first()
        )

        if conversation is None:
            conversation_subject = request.form.get(
                "subject",
                ""
            ).strip()

            if request.method == "POST" and not conversation_subject:
                return render_template(
                    "live_chat.html",
                    conversation=None,
                    chat_messages=[],
                    is_authenticated=True,
                    subject_error="Please enter a subject or reason for contacting Fairmont Bank Support."
                )

            if len(conversation_subject) > 200:
                conversation_subject = conversation_subject[:200]

            conversation = LiveChatConversation(
                customer_id=current_user.id,
                status="Open",
                subject=conversation_subject or "Bank Support"
            )

            db.session.add(conversation)
            db.session.commit()

        if request.method == "POST":
            message_text = request.form.get("message", "").strip()

            if message_text:
                if len(message_text) > 2000:
                    message_text = message_text[:2000]

                customer_message = LiveChatMessage(
                    conversation_id=conversation.id,
                    sender_type="customer",
                    sender_id=current_user.id,
                    message=message_text,
                    is_read=False,
                    created_at=datetime.utcnow()
                )

                conversation.updated_at = datetime.utcnow()

                db.session.add(customer_message)
                db.session.commit()

                session["live_chat_success"] = (
                    "Message sent successfully. "
                    "Your message has been delivered to Fairmont Bank Support."
                )

                return redirect(url_for("live_chat"))

        chat_messages = (
            LiveChatMessage.query
            .filter_by(conversation_id=conversation.id)
            .order_by(LiveChatMessage.created_at.asc())
            .all()
        )

        # Mark support messages as read when the customer opens the chat.
        unread_support = (
            LiveChatMessage.query
            .filter_by(
                conversation_id=conversation.id,
                sender_type="support",
                is_read=False
            )
            .all()
        )

        for message in unread_support:
            message.is_read = True

        if unread_support:
            db.session.commit()

        success_message = session.pop("live_chat_success", None)

        return render_template(
            "live_chat.html",
            conversation=conversation,
            chat_messages=chat_messages,
            is_authenticated=True,
            success_message=success_message,
            subject_error=None
        )

    # ---------------------------------------------------------
    # NOT LOGGED IN
    # ---------------------------------------------------------
    # The page can open from the login screen, but we do not
    # attach an anonymous visitor to a customer account.
    return render_template(
        "live_chat.html",
        conversation=None,
        chat_messages=[],
        is_authenticated=False
    )

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            return render_template(
                "admin_login.html",
                error="Please enter your username and password."
            )

        admin = AdminUser.query.filter_by(
            username=username
        ).first()

        if (
            admin is None
            or not admin.is_active
            or not check_password_hash(
                admin.password_hash,
                password
            )
        ):
            return render_template(
                "admin_login.html",
                error="Invalid administrator credentials."
            )

        session["admin_id"] = admin.id
        session["admin_username"] = admin.username

        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_id", None)
    session.pop("admin_username", None)

    return redirect(url_for("admin_login"))

# =========================================================
# ADMIN: VIRTUAL ATM CARD APPLICATIONS
# =========================================================

@app.route("/admin/virtual-card-applications")
def admin_virtual_card_applications():
    # Require administrator login.
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    admin = AdminUser.query.get(session["admin_id"])

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    applications = VirtualCardApplication.query.order_by(
        VirtualCardApplication.submitted_at.desc()
    ).all()

    return render_template(
        "admin_virtual_card_applications.html",
        applications=applications
    )


@app.route(
    "/admin/virtual-card-applications/<int:application_id>/review",
    methods=["POST"]
)
def admin_review_virtual_card_application(application_id):
    # Require administrator login.
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    admin = AdminUser.query.get(session["admin_id"])

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    application = db.session.get(
        VirtualCardApplication,
        application_id
    )

    if application is None:
        flash("Application not found.", "error")
        return redirect(
            url_for("admin_virtual_card_applications")
        )

    # Only pending applications can be reviewed.
    if application.status != "Pending":
        flash(
            "This application has already been reviewed.",
            "error"
        )
        return redirect(
            url_for("admin_virtual_card_applications")
        )

    action = request.form.get("action", "").strip().lower()

    if action == "approve":
        existing_card = VirtualATMCard.query.filter_by(
            customer_id=application.customer_id
        ).first()

        if existing_card is None:
            card = VirtualATMCard(
                customer_id=application.customer_id,
                card_number=generate_virtual_card_number(),
                expiry_date=generate_virtual_card_expiry(),
                security_code=generate_virtual_card_security_code(),
                status="Active"
            )
            db.session.add(card)
        elif existing_card.status == "Cancelled":
            # Issue replacement credentials only after admin approval.
            existing_card.card_number = generate_virtual_card_number()
            existing_card.expiry_date = generate_virtual_card_expiry()
            existing_card.security_code = generate_virtual_card_security_code()
            existing_card.status = "Active"
            existing_card.created_at = datetime.utcnow()
        else:
            flash(
                "This customer already has a card that is not cancelled.",
                "error"
            )
            return redirect(
                url_for("admin_virtual_card_applications")
            )

        application.status = "Approved"
        application.reviewed_at = datetime.utcnow()
        application.reviewed_by = admin.username
        application.rejection_reason = None

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                "The application could not be approved. "
                "Please check the database and try again.",
                "error"
            )
            return redirect(
                url_for("admin_virtual_card_applications")
            )

        create_customer_notification(
            application.customer_id,
            "Virtual card application approved",
            "Your virtual ATM card application has been approved. You can review your card details from your account dashboard.",
            notification_type="Account",
        )

        flash(
            "Virtual card application approved.",
            "success"
        )

    elif action == "reject":
        reason = request.form.get(
            "rejection_reason", ""
        ).strip()

        application.status = "Rejected"
        application.reviewed_at = datetime.utcnow()
        application.reviewed_by = admin.username
        application.rejection_reason = (
            reason[:255] if reason else "Application rejected."
        )

        db.session.commit()

        create_customer_notification(
            application.customer_id,
            "Virtual card application update",
            f"Your virtual ATM card application was not approved. Reason: {application.rejection_reason}",
            notification_type="Account",
        )

        flash(
            "Virtual card application rejected.",
            "success"
        )

    else:
        flash("Invalid review action.", "error")

    return redirect(
        url_for("admin_virtual_card_applications")
    )


# =========================================================
# ADMIN CONTROLLED CUSTOMER LOGIN OTP
# =========================================================

@app.route("/admin/customer/<int:customer_id>/toggle-login-otp", methods=["POST"])
def admin_toggle_customer_login_otp(customer_id):

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if not admin or not admin.is_active:
        session.pop("admin_id", None)
        return redirect(url_for("admin_login"))

    customer = db.session.get(Customer, customer_id)

    if customer is None:
        flash("Customer could not be found.", "error")
        return redirect(url_for("admin_customers"))

    customer.login_otp_enabled = not bool(
        customer.login_otp_enabled
    )

    db.session.commit()

    if customer.login_otp_enabled:
        flash(
            f"Login OTP has been enabled for {customer.full_name}.",
            "success"
        )
    else:
        flash(
            f"Login OTP has been disabled for {customer.full_name}.",
            "success"
        )

    return redirect(
        url_for(
            "admin_customer_profile",
            customer_id=customer.id
        )
    )


@app.route("/admin/login-otp-requests")
def admin_login_otp_requests():

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if not admin or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    # Get all unused OTP records, newest first.
    otp_records = (
        CustomerLoginOTP.query
        .filter_by(used=False)
        .order_by(CustomerLoginOTP.created_at.desc())
        .all()
    )

    active_requests = []

    now = datetime.utcnow()

    for otp in otp_records:

        if not otp.expires_at:
            continue

        expires_at = otp.expires_at

        # SQLite may return naive datetimes.
        if expires_at.tzinfo is not None:
            expires_at = expires_at.astimezone(
                timezone.utc
            ).replace(tzinfo=None)

        # Expired OTPs are automatically marked used.
        if now >= expires_at:
            otp.used = True
            continue

        customer = db.session.get(
            Customer,
            otp.customer_id
        )

        if customer is None:
            continue

        # Only show OTPs for customers who are currently
        # controlled by the administrator.
        if not customer.login_otp_enabled:
            continue

        active_requests.append({
            "otp": otp,
            "customer": customer
        })

    db.session.commit()

    return render_template(
        "admin_login_otp_requests.html",
        admin=admin,
        otp_requests=active_requests
    )


@app.route("/admin/login-otp/<int:otp_id>/mark-used", methods=["POST"])
def admin_mark_login_otp_used(otp_id):

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if not admin or not admin.is_active:
        session.pop("admin_id", None)
        return redirect(url_for("admin_login"))

    otp = db.session.get(CustomerLoginOTP, otp_id)

    if otp:
        otp.used = True
        db.session.commit()

    return redirect(
        url_for("admin_login_otp_requests")
    )




# =========================================================
# BILLS & INVOICES
# =========================================================

BILLING_TYPES = [
    "TCC Tax / Government Tax Assessment",
    "TCC Processing Fee",
    "Account Maintenance Fee",
    "Account Service Fee",
    "International Transfer Fee",
    "Wire Transfer Fee",
    "Currency Conversion Fee",
    "Compliance / Verification Fee",
    "Document Processing Fee",
    "Banking Service Charge",
    "Other Customer Billing",
]


def _admin_invoice_guard():
    """Return a redirect response when an administrator is not signed in."""
    admin_id = session.get("admin_id")
    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)
    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    return None


def _refresh_invoice_status(invoice):
    """Update a pending invoice to Overdue when its due date has passed."""
    if (
        invoice.status == "Pending"
        and invoice.due_date is not None
        and invoice.due_date < datetime.utcnow().date()
    ):
        invoice.status = "Overdue"
        return True
    return False


def generate_bank_invoice_number():
    """Generate a unique customer billing invoice number."""
    while True:
        number = (
            f"FB-INV-{datetime.utcnow().strftime('%Y%m%d')}-"
            f"{secrets.token_hex(3).upper()}"
        )
        if not BankInvoice.query.filter_by(invoice_number=number).first():
            return number


@app.route("/admin/invoices")
def admin_invoices():
    guard = _admin_invoice_guard()
    if guard:
        return guard

    invoices = BankInvoice.query.order_by(
        BankInvoice.created_at.desc(), BankInvoice.id.desc()
    ).all()

    changed = False
    for invoice in invoices:
        if _refresh_invoice_status(invoice):
            changed = True
    if changed:
        db.session.commit()

    customers = {
        customer.customer_id: customer
        for customer in Customer.query.all()
    }

    return render_template(
        "admin_invoices.html",
        invoices=invoices,
        customers=customers,
    )


@app.route("/admin/invoices/create", methods=["GET", "POST"])
def admin_create_invoice():
    guard = _admin_invoice_guard()
    if guard:
        return guard

    customers = Customer.query.order_by(Customer.full_name.asc()).all()
    form = request.form if request.method == "POST" else {}
    errors = []
    today = datetime.utcnow().date().isoformat()

    if request.method == "POST":
        customer_id = request.form.get("customer_id", "").strip()
        billing_type = request.form.get("billing_type", "").strip()
        description = request.form.get("description", "").strip()

        customer = Customer.query.filter_by(customer_id=customer_id).first()
        if customer is None:
            errors.append("Please select a valid customer.")
        if not billing_type:
            errors.append("Please select a billing type.")
        if not description:
            errors.append("Please enter a description.")

        def money_field(name, label):
            raw = request.form.get(name, "0").strip()
            if raw == "":
                return 0.0
            try:
                value = float(raw)
            except (TypeError, ValueError):
                errors.append(f"{label} must be a valid number.")
                return 0.0
            if value < 0:
                errors.append(f"{label} cannot be negative.")
                return 0.0
            return round(value, 2)

        amount = money_field("amount", "Base amount")
        tcc_tax = money_field("tcc_tax", "TCC tax")
        other_fee = money_field("other_fee", "Other fee")
        discount = money_field("discount", "Discount")

        due_date = None
        due_date_raw = request.form.get("due_date", "").strip()
        if due_date_raw:
            try:
                due_date = datetime.strptime(due_date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Please enter a valid due date.")
        else:
            errors.append("Please enter a due date.")

        if discount > amount + tcc_tax + other_fee:
            errors.append("Discount cannot be greater than the invoice charges.")

        if not errors:
            total = round(amount + tcc_tax + other_fee - discount, 2)
            invoice = BankInvoice(
                invoice_number=generate_bank_invoice_number(),
                customer_id=customer.customer_id,
                billing_type=billing_type,
                description=description,
                amount=amount,
                tcc_tax=tcc_tax,
                other_fee=other_fee,
                discount=discount,
                total=total,
                currency=(
                    request.form.get("currency", "GBP").strip().upper()
                    or "GBP"
                ),
                issue_date=datetime.utcnow().date(),
                due_date=due_date,
                status="Pending",
                billing_note=request.form.get("billing_note", "").strip() or None,
                created_by=session.get("admin_username"),
            )

            db.session.add(invoice)
            db.session.commit()

            flash(
                f"Invoice {invoice.invoice_number} created successfully.",
                "success",
            )
            return redirect(
                url_for("admin_invoice_detail", invoice_id=invoice.id)
            )

    return render_template(
        "admin_invoice_create.html",
        customers=customers,
        billing_types=BILLING_TYPES,
        form=form,
        errors=errors,
        today=today,
    )


@app.route("/admin/invoices/<int:invoice_id>")
def admin_invoice_detail(invoice_id):
    guard = _admin_invoice_guard()
    if guard:
        return guard

    invoice = db.session.get(BankInvoice, invoice_id)
    if invoice is None:
        return "Invoice not found", 404

    if _refresh_invoice_status(invoice):
        db.session.commit()

    # The admin invoice detail template displays the customer name and ID.
    # Load the customer linked to this invoice before rendering.
    customer = Customer.query.filter_by(
        customer_id=invoice.customer_id
    ).first()

    if customer is None:
        return "Customer associated with this invoice was not found", 404

    return render_template(
        "admin_invoice_detail.html",
        invoice=invoice,
        customer=customer,
    )


@app.route("/admin/invoices/<int:invoice_id>/mark-paid", methods=["POST"])
def admin_mark_invoice_paid(invoice_id):
    guard = _admin_invoice_guard()
    if guard:
        return guard

    invoice = db.session.get(BankInvoice, invoice_id)
    if invoice is None:
        return "Invoice not found", 404

    if invoice.status == "Cancelled":
        flash("A cancelled invoice cannot be marked as paid.", "error")
        return redirect(url_for("admin_invoice_detail", invoice_id=invoice.id))

    invoice.status = "Paid"
    payment_reference = request.form.get("payment_reference", "").strip()
    invoice.payment_reference = payment_reference or invoice.payment_reference
    invoice.paid_at = datetime.utcnow()

    db.session.commit()

    flash(f"Invoice {invoice.invoice_number} marked as paid.", "success")
    return redirect(url_for("admin_invoice_detail", invoice_id=invoice.id))


@app.route("/admin/invoices/<int:invoice_id>/cancel", methods=["POST"])
def admin_cancel_invoice(invoice_id):
    guard = _admin_invoice_guard()
    if guard:
        return guard

    invoice = db.session.get(BankInvoice, invoice_id)
    if invoice is None:
        return "Invoice not found", 404

    if invoice.status == "Paid":
        flash("A paid invoice cannot be cancelled.", "error")
        return redirect(url_for("admin_invoice_detail", invoice_id=invoice.id))

    invoice.status = "Cancelled"
    db.session.commit()

    flash(f"Invoice {invoice.invoice_number} cancelled.", "success")
    return redirect(url_for("admin_invoice_detail", invoice_id=invoice.id))


@app.route("/admin/invoices/<int:invoice_id>/print")
def admin_print_invoice(invoice_id):
    guard = _admin_invoice_guard()
    if guard:
        return guard

    invoice = db.session.get(BankInvoice, invoice_id)
    if invoice is None:
        return "Invoice not found", 404

    return render_template("admin_invoice_detail.html", invoice=invoice)


@app.route("/invoices")
def customer_invoices():
    customer_id = session.get("customer_id")
    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(customer_id=customer_id).first()
    if customer is None:
        session.pop("customer_id", None)
        return redirect(url_for("login"))

    invoices = BankInvoice.query.filter_by(
        customer_id=customer.customer_id
    ).order_by(
        BankInvoice.issue_date.desc(), BankInvoice.id.desc()
    ).all()

    changed = False
    for invoice in invoices:
        if _refresh_invoice_status(invoice):
            changed = True
    if changed:
        db.session.commit()

    return render_template("invoices.html", invoices=invoices)


@app.route("/invoices/<int:invoice_id>")
def customer_invoice_detail(invoice_id):
    customer_id = session.get("customer_id")
    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(customer_id=customer_id).first()
    if customer is None:
        session.pop("customer_id", None)
        return redirect(url_for("login"))

    invoice = BankInvoice.query.filter_by(
        id=invoice_id,
        customer_id=customer.customer_id,
    ).first()

    if invoice is None:
        return "Invoice not found", 404

    if _refresh_invoice_status(invoice):
        db.session.commit()

    return render_template(
        "invoice_detail.html",
        invoice=invoice,
        customer=customer,
    )


@app.route("/admin")
def admin_dashboard():

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)

        return redirect(url_for("admin_login"))

    return render_template(
        "admin_dashboard.html",
        admin=admin
    )




@app.route("/admin/live-chat", methods=["GET", "POST"])
def admin_live_chat():
    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    conversation_id = request.args.get("conversation_id", type=int)

    if request.method == "POST":
        conversation_id = request.form.get("conversation_id", type=int)
        message_text = request.form.get("message", "").strip()

        if not conversation_id:
            return redirect(url_for("admin_live_chat"))

        conversation = db.session.get(
            LiveChatConversation,
            conversation_id
        )

        if conversation is None:
            return redirect(url_for("admin_live_chat"))

        if not message_text:
            return redirect(
                url_for(
                    "admin_live_chat",
                    conversation_id=conversation.id
                )
            )

        if len(message_text) > 2000:
            message_text = message_text[:2000]

        message = LiveChatMessage(
            conversation_id=conversation.id,
            sender_type="support",
            sender_id=admin.id,
            message=message_text,
            is_read=False
        )

        conversation.status = "Open"
        conversation.updated_at = datetime.utcnow()

        db.session.add(message)
        db.session.commit()

        return redirect(
            url_for(
                "admin_live_chat",
                conversation_id=conversation.id
            )
        )

    conversations = (
        LiveChatConversation.query
        .order_by(LiveChatConversation.updated_at.desc())
        .all()
    )

    selected_conversation = None
    messages = []

    if conversation_id:
        selected_conversation = db.session.get(
            LiveChatConversation,
            conversation_id
        )

        if selected_conversation:
            messages = (
                LiveChatMessage.query
                .filter_by(
                    conversation_id=selected_conversation.id
                )
                .order_by(LiveChatMessage.created_at.asc())
                .all()
            )

            unread_customer_messages = (
                LiveChatMessage.query
                .filter_by(
                    conversation_id=selected_conversation.id,
                    sender_type="customer",
                    is_read=False
                )
                .all()
            )

            for customer_message in unread_customer_messages:
                customer_message.is_read = True

            if unread_customer_messages:
                db.session.commit()

    customers = {}

    for conversation in conversations:
        customer = db.session.get(
            Customer,
            conversation.customer_id
        )

        customers[conversation.id] = customer

    return render_template(
        "admin_live_chat.html",
        admin=admin,
        conversations=conversations,
        selected_conversation=selected_conversation,
        messages=messages,
        customers=customers
    )


@app.route("/admin/bank-email", methods=["GET", "POST"])
def admin_bank_email():
    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    message_id = request.args.get("message_id", type=int)

    if request.method == "POST":
        message_id = request.form.get("message_id", type=int)
        reply_text = request.form.get("reply", "").strip()

        if not message_id:
            return redirect(url_for("admin_bank_email"))

        bank_message = db.session.get(
            BankMessage,
            message_id
        )

        if bank_message is None:
            return redirect(url_for("admin_bank_email"))

        if not reply_text:
            return redirect(
                url_for(
                    "admin_bank_email",
                    message_id=bank_message.id
                )
            )

        if len(reply_text) > 5000:
            reply_text = reply_text[:5000]

        # Store the administrator reply as a new BankMessage
        # belonging to the same customer.
        reply_message = BankMessage(
            customer_id=bank_message.customer_id,
            subject="Re: " + bank_message.subject,
            message=reply_text,
            status="Unread",
            created_at=datetime.utcnow()
        )

        db.session.add(reply_message)

        # Mark the customer's original message as read.
        bank_message.status = "Read"

        db.session.commit()

        return redirect(
            url_for(
                "admin_bank_email",
                message_id=bank_message.id
            )
        )

    messages = (
        BankMessage.query
        .order_by(BankMessage.created_at.desc())
        .all()
    )

    customers = {}

    for bank_message in messages:
        customer = db.session.get(
            Customer,
            bank_message.customer_id
        )
        customers[bank_message.id] = customer

    selected_message = None
    selected_customer = None

    if message_id:
        selected_message = db.session.get(
            BankMessage,
            message_id
        )

        if selected_message:
            selected_customer = db.session.get(
                Customer,
                selected_message.customer_id
            )

            # Opening a customer's message marks it as read.
            if selected_message.status == "Unread":
                selected_message.status = "Read"
                db.session.commit()

    return render_template(
        "admin_bank_email.html",
        admin=admin,
        messages=messages,
        customers=customers,
        selected_message=selected_message,
        selected_customer=selected_customer
    )


@app.route("/admin/customers")
def admin_customers():
    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    search = request.args.get("search", "").strip()

    query = Customer.query

    if search:
        pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                Customer.customer_id.ilike(pattern),
                Customer.account_number.ilike(pattern),
                Customer.full_name.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.phone.ilike(pattern)
            )
        )

    customers = (
        query
        .order_by(Customer.id.desc())
        .all()
    )

    return render_template(
        "admin_customers.html",
        admin=admin,
        customers=customers,
        search=search
    )




# ============================================================
# ADMIN â€” CUSTOMER TCC PAYMENT RESTRICTION
# ============================================================

@app.route(
    "/admin/customer/<int:customer_id>/tcc-restriction",
    methods=["POST"]
)
def admin_toggle_tcc_restriction(customer_id):

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    customer = db.session.get(Customer, customer_id)

    if customer is None:
        flash(
            "The selected customer could not be found.",
            "error"
        )
        return redirect(url_for("admin_customers"))

    action = request.form.get(
        "tcc_action",
        ""
    ).strip().lower()

    if action == "enable":

        customer.tcc_payment_restriction_enabled = True

        flash(
            "TCC Payment Restriction has been enabled for "
            f"{customer.full_name}.",
            "success"
        )

    elif action == "disable":

        customer.tcc_payment_restriction_enabled = False

        flash(
            "TCC Payment Restriction has been disabled for "
            f"{customer.full_name}.",
            "success"
        )

    else:

        flash(
            "Invalid TCC restriction action.",
            "error"
        )

    db.session.commit()

    return redirect(
        url_for(
            "admin_customer_profile",
            customer_id=customer.id
        )
    )




# ============================================================
# ADMIN - FREEZE / UNFREEZE CUSTOMER ACCOUNT
# ============================================================

@app.route(
    "/admin/customer/<int:customer_id>/toggle-freeze",
    methods=["POST"]
)
def admin_toggle_customer_freeze(customer_id):

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    customer = db.session.get(Customer, customer_id)

    if customer is None:
        flash(
            "The selected customer could not be found.",
            "error"
        )
        return redirect(url_for("admin_customers"))

    if customer.account_status == "Locked":

        customer.account_status = "Active"

        flash(
            f"{customer.full_name}'s account has been unfrozen.",
            "success"
        )

    else:

        customer.account_status = "Locked"

        # Disable OTP while the account is frozen.
        customer.login_otp_enabled = False

        flash(
            f"{customer.full_name}'s account has been frozen.",
            "success"
        )

    db.session.commit()

    return redirect(
        url_for(
            "admin_customer_profile",
            customer_id=customer.id
        )
    )




# ============================================================
# ADMIN - PERMANENTLY DELETE CUSTOMER
# ============================================================

@app.route(
    "/admin/customer/<int:customer_id>/delete",
    methods=["POST"]
)
def admin_delete_customer(customer_id):

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    customer = db.session.get(Customer, customer_id)

    if customer is None:
        flash(
            "The selected customer could not be found.",
            "error"
        )
        return redirect(url_for("admin_customers"))

    customer_name = customer.full_name
    customer_code = customer.customer_id

    try:

        # -----------------------------------------------------
        # Remove related records before deleting the customer.
        #
        # This uses the SQLAlchemy model metadata so the cleanup
        # works with the existing database structure.
        # -----------------------------------------------------

        for model in list(db.Model.registry._class_registry.values()):

            if not isinstance(model, type):
                continue

            if not hasattr(model, "__table__"):
                continue

            if model is Customer:
                continue

            table = model.__table__

            # Look for direct customer_id references.
            customer_id_column = table.columns.get("customer_id")

            if customer_id_column is not None:

                try:

                    query = db.session.query(model).filter(
                        customer_id_column == customer.id
                    )

                    rows = query.all()

                    for row in rows:
                        db.session.delete(row)

                except Exception:
                    pass

            # Some application tables use the public
            # Customer ID string instead of the numeric DB ID.
            customer_code_column = table.columns.get("customer_id")

            if customer_code_column is not None:

                try:

                    rows = (
                        db.session.query(model)
                        .filter(
                            customer_code_column == customer_code
                        )
                        .all()
                    )

                    for row in rows:
                        if row not in db.session.deleted:
                            db.session.delete(row)

                except Exception:
                    pass

            # Handle tables using recipient_customer_id.
            recipient_column = table.columns.get(
                "recipient_customer_id"
            )

            if recipient_column is not None:

                try:

                    rows = (
                        db.session.query(model)
                        .filter(
                            recipient_column == customer_code
                        )
                        .all()
                    )

                    for row in rows:
                        if row not in db.session.deleted:
                            db.session.delete(row)

                except Exception:
                    pass

        # -----------------------------------------------------
        # Delete the customer itself.
        # -----------------------------------------------------

        db.session.delete(customer)

        db.session.commit()

        # Remove customer login session if applicable.
        session.pop("customer_id", None)
        session.pop("pending_login_customer_id", None)

        flash(
            f"Customer {customer_name} ({customer_code}) "
            "has been permanently deleted.",
            "success"
        )

        return redirect(
            url_for("admin_customers")
        )

    except Exception as exc:

        db.session.rollback()

        print(
            "CUSTOMER DELETE ERROR:",
            repr(exc)
        )

        flash(
            "The customer could not be deleted because "
            "related account data could not be safely removed.",
            "error"
        )

        return redirect(
            url_for(
                "admin_customer_profile",
                customer_id=customer.id
            )
        )


@app.route("/admin/customer/<int:customer_id>")
def admin_customer_profile(customer_id):
    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    customer = db.session.get(Customer, customer_id)

    if customer is None:
        return redirect(url_for("admin_customers"))

    customer_transactions = (
        Transaction.query
        .filter_by(customer_id=customer.customer_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    customer_bank_messages = (
    BankMessage.query
    .filter_by(customer_id=customer.id)
    .order_by(BankMessage.created_at.desc())
    .all()
)
    customer_conversations = (
        LiveChatConversation.query
        .filter_by(customer_id=customer.id)
        .order_by(LiveChatConversation.updated_at.desc())
        .all()
    )

    return render_template(
        "admin_customer_profile.html",
        admin=admin,
        customer=customer,
        customer_transactions=customer_transactions,
        customer_bank_messages=customer_bank_messages,
        customer_conversations=customer_conversations
    )

# ============================================================
# ADMIN — ACCOUNT APPLICATION APPROVAL
# ============================================================

@app.route("/admin/customer/<int:customer_id>/approve", methods=["POST"])
def admin_approve_customer(customer_id):

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    customer = db.session.get(Customer, customer_id)

    if customer is None:
        flash("Customer account was not found.", "error")
        return redirect(url_for("admin_accounts"))

    if customer.account_status != "Pending Approval":
        flash("This account is not pending approval.", "error")
        return redirect(
            url_for(
                "admin_customer_profile",
                customer_id=customer.id
            )
        )

    customer.account_status = "Active"

    db.session.commit()

    if not send_account_status_email(customer, customer.account_status):
        app.logger.warning(
            "Account approval email could not be sent for customer %s",
            customer.customer_id,
        )

    flash(
        f"Account application for {customer.full_name} has been approved.",
        "success"
    )

    return redirect(
        url_for(
            "admin_customer_profile",
            customer_id=customer.id
        )
    )


@app.route("/admin/customer/<int:customer_id>/reject", methods=["POST"])
def admin_reject_customer(customer_id):

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    customer = db.session.get(Customer, customer_id)

    if customer is None:
        flash("Customer account was not found.", "error")
        return redirect(url_for("admin_accounts"))

    if customer.account_status != "Pending Approval":
        flash("This account is not pending approval.", "error")
        return redirect(
            url_for(
                "admin_customer_profile",
                customer_id=customer.id
            )
        )

    customer.account_status = "Rejected"

    db.session.commit()

    if not send_account_status_email(customer, customer.account_status):
        app.logger.warning(
            "Account rejection email could not be sent for customer %s",
            customer.customer_id,
        )

    flash(
        f"Account application for {customer.full_name} has been rejected.",
        "success"
    )

    return redirect(
        url_for(
            "admin_customer_profile",
            customer_id=customer.id
        )
    )



# ============================================================
# ADMIN — EDIT CUSTOMER DETAILS
# ============================================================

@app.route(
    "/admin/customer/<int:customer_id>/edit",
    methods=["GET", "POST"]
)
def admin_edit_customer(customer_id):

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    customer = db.session.get(Customer, customer_id)

    if customer is None:
        return redirect(url_for("admin_customers"))

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        country = request.form.get(
            "country",
            ""
        ).strip()

        account_type = request.form.get(
            "account_type",
            ""
        ).strip().lower()

        account_status = request.form.get(
            "account_status",
            ""
        ).strip()

        if not full_name:
            flash(
                "Customer full name is required.",
                "error"
            )

            return render_template(
                "admin_edit_customer.html",
                admin=admin,
                customer=customer
            )

        if not email:
            flash(
                "Customer email address is required.",
                "error"
            )

            return render_template(
                "admin_edit_customer.html",
                admin=admin,
                customer=customer
            )

        if not phone:
            flash(
                "Customer phone number is required.",
                "error"
            )

            return render_template(
                "admin_edit_customer.html",
                admin=admin,
                customer=customer
            )

        if not country:
            flash(
                "Customer country is required.",
                "error"
            )

            return render_template(
                "admin_edit_customer.html",
                admin=admin,
                customer=customer
            )

        if account_type not in {
            "savings",
            "current"
        }:
            flash(
                "Please select a valid account type.",
                "error"
            )

            return render_template(
                "admin_edit_customer.html",
                admin=admin,
                customer=customer
            )

        if not account_status:
            flash(
                "Please select an account status.",
                "error"
            )

            return render_template(
                "admin_edit_customer.html",
                admin=admin,
                customer=customer
            )

        existing_email = Customer.query.filter(
            Customer.email == email,
            Customer.id != customer.id
        ).first()

        if existing_email:
            flash(
                "Another customer is already using that email address.",
                "error"
            )

            return render_template(
                "admin_edit_customer.html",
                admin=admin,
                customer=customer
            )

        existing_phone = Customer.query.filter(
            Customer.phone == phone,
            Customer.id != customer.id
        ).first()

        if existing_phone:
            flash(
                "Another customer is already using that phone number.",
                "error"
            )

            return render_template(
                "admin_edit_customer.html",
                admin=admin,
                customer=customer
            )

        customer.full_name = full_name
        customer.email = email
        customer.phone = phone
        customer.country = country
        customer.account_type = account_type
        customer.account_status = account_status

        db.session.commit()

        flash(
            "Customer details updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "admin_customer_profile",
                customer_id=customer.id
            )
        )

    return render_template(
        "admin_edit_customer.html",
        admin=admin,
        customer=customer
    )


@app.route("/admin/transactions")
def admin_transactions():
    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if not admin or not admin.is_active:
        session.pop("admin_id", None)
        return redirect(url_for("admin_login"))

    search = request.args.get("search", "").strip()
    direction = request.args.get("direction", "").strip()
    status = request.args.get("status", "").strip()

    query = Transaction.query

    if search:
        search_value = f"%{search}%"

        customer_ids = [
            customer.customer_id
            for customer in Customer.query.filter(
                db.or_(
                    Customer.customer_id.ilike(search_value),
                    Customer.full_name.ilike(search_value),
                    Customer.email.ilike(search_value),
                    Customer.account_number.ilike(search_value),
                )
            ).all()
        ]

        search_conditions = [
            Transaction.transaction_reference.ilike(search_value),
            Transaction.customer_id.ilike(search_value),
            Transaction.description.ilike(search_value),
            Transaction.counterparty.ilike(search_value),
        ]

        if customer_ids:
            search_conditions.append(
                Transaction.customer_id.in_(customer_ids)
            )

        query = query.filter(db.or_(*search_conditions))

    if direction in ("Debit", "Credit"):
        query = query.filter(Transaction.direction == direction)

    if status:
        query = query.filter(Transaction.status == status)

    transactions = query.order_by(
        Transaction.id.desc()
    ).all()

    customer_map = {}

    customer_ids = {
        transaction.customer_id
        for transaction in transactions
        if transaction.customer_id
    }

    if customer_ids:
        customers = Customer.query.filter(
            Customer.customer_id.in_(customer_ids)
        ).all()

        customer_map = {
            customer.customer_id: customer
            for customer in customers
        }

    return render_template(
        "admin_transactions.html",
        admin=admin,
        transactions=transactions,
        customer_map=customer_map,
        search=search,
        direction=direction,
        status=status,
    )




@app.route("/admin/accounts")
def admin_accounts():
    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if not admin or not admin.is_active:
        session.pop("admin_id", None)
        return redirect(url_for("admin_login"))

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    account_type = request.args.get("account_type", "").strip()

    query = Customer.query

    if search:
        search_value = f"%{search}%"

        query = query.filter(
            db.or_(
                Customer.customer_id.ilike(search_value),
                Customer.account_number.ilike(search_value),
                Customer.full_name.ilike(search_value),
                Customer.email.ilike(search_value),
                Customer.phone.ilike(search_value),
            )
        )

    if status:
        query = query.filter(Customer.account_status == status)

    if account_type:
        query = query.filter(Customer.account_type == account_type)

    customers = query.order_by(Customer.id.desc()).all()

    return render_template(
        "admin_accounts.html",
        admin=admin,
        customers=customers,
        search=search,
        status=status,
        account_type=account_type,
    )



# ============================================================
# ADMIN â€” POST INCOMING PAYMENT
# ============================================================



# ============================================================
# ADMIN â€” TCC VERIFICATION REQUESTS
# ============================================================

@app.route("/admin/tcc-requests")
def admin_tcc_requests():

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    requests_list = (
        PaymentApproval.query
        .filter(
            PaymentApproval.tcc_status == "Required"
        )
        .order_by(
            PaymentApproval.created_at.desc()
        )
        .all()
    )

    customers = {}

    for payment in requests_list:

        customer = Customer.query.filter_by(
            customer_id=payment.customer_id
        ).first()

        customers[payment.id] = customer

    return render_template(
        "admin_tcc_requests.html",
        admin=admin,
        requests_list=requests_list,
        customers=customers
    )


@app.route("/admin/payment-approvals")
def admin_payment_approvals():
    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    status_filter = request.args.get("status", "Pending Approval").strip()

    allowed_statuses = {
        "Pending Approval",
        "Approved",
        "Rejected",
        "All"
    }

    if status_filter not in allowed_statuses:
        status_filter = "Pending Approval"

    query = PaymentApproval.query

    if status_filter != "All":
        query = query.filter_by(status=status_filter)

    approvals = query.order_by(
        PaymentApproval.created_at.desc()
    ).all()

    customer_map = {}

    customer_ids = {
        approval.customer_id
        for approval in approvals
        if approval.customer_id
    }

    if customer_ids:
        customers = Customer.query.filter(
            Customer.customer_id.in_(customer_ids)
        ).all()

        customer_map = {
            customer.customer_id: customer
            for customer in customers
        }

    pending_count = PaymentApproval.query.filter_by(
        status="Pending Approval"
    ).count()

    approved_count = PaymentApproval.query.filter_by(
        status="Approved"
    ).count()

    rejected_count = PaymentApproval.query.filter_by(
        status="Rejected"
    ).count()

    return render_template(
        "admin_payment_approvals.html",
        admin=admin,
        approvals=approvals,
        customer_map=customer_map,
        status_filter=status_filter,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count
    )


@app.route("/admin/incoming-payment", methods=["GET", "POST"])

@app.route(
    "/admin/payment-approval/<int:approval_id>",
    methods=["GET", "POST"]
)
def admin_review_payment(approval_id):

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    approval = db.session.get(
        PaymentApproval,
        approval_id
    )

    if approval is None:
        return redirect(url_for("admin_payment_approvals"))

    customer = Customer.query.filter_by(
        customer_id=approval.customer_id
    ).first()

    recipient = None

    if approval.recipient_customer_id:
        recipient = Customer.query.filter_by(
            customer_id=approval.recipient_customer_id
        ).first()

    if request.method == "GET":
        return render_template(
            "admin_payment_approval_review.html",
            admin=admin,
            approval=approval,
            customer=customer,
            recipient=recipient
        )

    action = request.form.get(
        "action",
        ""
    ).strip().lower()

    if approval.status != "Pending Approval":
        flash(
            "This payment has already been reviewed.",
            "error"
        )
        return redirect(
            url_for(
                "admin_review_payment",
                approval_id=approval.id
            )
        )

    if action == "reject":

        rejection_reason = request.form.get(
            "rejection_reason",
            ""
        ).strip()

        approval.status = "Rejected"
        approval.reviewed_at = datetime.utcnow()
        approval.reviewed_by = admin.username
        approval.rejection_reason = (
            rejection_reason
            or "Payment rejected by Fairmont Bank Support."
        )

        if approval.payment_type == "International Transfer":
            external_transfer = None
            if approval.original_transaction_reference:
                external_transfer = ExternalTransfer.query.filter_by(
                    transaction_reference=approval.original_transaction_reference
                ).first()
            if external_transfer is not None:
                external_transfer.status = "Rejected"

        db.session.commit()

        if not send_payment_status_email(customer, approval, event="rejected"):
            app.logger.warning(
                "Payment rejection email could not be sent for reference %s",
                approval.payment_reference,
            )

        flash(
            "Payment request rejected. No customer balance was changed.",
            "success"
        )

        return redirect(
            url_for(
                "admin_payment_approvals",
                status="Pending Approval"
            )
        )

    if action != "approve":
        flash("Invalid approval action.", "error")
        return redirect(
            url_for(
                "admin_review_payment",
                approval_id=approval.id
            )
        )

    if customer is None:
        flash(
            "The customer account associated with this payment could not be found.",
            "error"
        )
        return redirect(
            url_for(
                "admin_review_payment",
                approval_id=approval.id
            )
        )

    if str(customer.account_status).lower() != "active":
        flash(
            "The customer account is not active.",
            "error"
        )
        return redirect(
            url_for(
                "admin_review_payment",
                approval_id=approval.id
            )
        )

    amount = float(approval.amount)
    transactions_to_notify = []

    # Internal Fairmont transfer:
    # debit sender and credit recipient in the same database transaction.
    if (
        approval.payment_type == "Bank Transfer"
        and approval.recipient_customer_id
    ):

        if recipient is None:
            flash(
                "The recipient account could not be found.",
                "error"
            )
            return redirect(
                url_for(
                    "admin_review_payment",
                    approval_id=approval.id
                )
            )

        if str(recipient.account_status).lower() != "active":
            flash(
                "The recipient account is not active.",
                "error"
            )
            return redirect(
                url_for(
                    "admin_review_payment",
                    approval_id=approval.id
                )
            )

        current_sender_balance = float(
            customer.account_balance or 0
        )

        if amount > current_sender_balance:
            flash(
                "The sender no longer has sufficient available balance.",
                "error"
            )
            return redirect(
                url_for(
                    "admin_review_payment",
                    approval_id=approval.id
                )
            )

        sender_new_balance = (
            current_sender_balance - amount
        )

        recipient_new_balance = (
            float(recipient.account_balance or 0)
            + amount
        )

        customer.account_balance = sender_new_balance
        recipient.account_balance = recipient_new_balance

        sender_transaction = Transaction(
            transaction_reference=generate_transaction_reference(),
            customer_id=customer.customer_id,
            transaction_type="Bank Transfer",
            direction="Debit",
            amount=amount,
            balance_after=sender_new_balance,
            description=approval.description,
            counterparty=recipient.full_name,
            status="Completed"
        )

        recipient_transaction = Transaction(
            transaction_reference=generate_transaction_reference(),
            customer_id=recipient.customer_id,
            transaction_type="Bank Transfer",
            direction="Credit",
            amount=amount,
            balance_after=recipient_new_balance,
            description=approval.description,
            counterparty=customer.full_name,
            status="Completed"
        )

        db.session.add(sender_transaction)
        db.session.add(recipient_transaction)
        transactions_to_notify.extend([sender_transaction, recipient_transaction])

    elif approval.payment_type == "International Transfer":

        current_balance = float(customer.account_balance or 0)

        if amount > current_balance:
            flash(
                "The customer no longer has sufficient available balance.",
                "error"
            )
            return redirect(
                url_for(
                    "admin_review_payment",
                    approval_id=approval.id
                )
            )

        new_balance = current_balance - amount
        customer.account_balance = new_balance

        transaction = Transaction(
            transaction_reference=generate_transaction_reference(),
            customer_id=customer.customer_id,
            transaction_type="International Transfer",
            direction="Debit",
            amount=amount,
            balance_after=new_balance,
            description=approval.description,
            counterparty=approval.counterparty,
            status="Completed"
        )

        db.session.add(transaction)
        transactions_to_notify.append(transaction)

        external_transfer = None
        if approval.original_transaction_reference:
            external_transfer = ExternalTransfer.query.filter_by(
                transaction_reference=approval.original_transaction_reference
            ).first()

        if external_transfer is not None:
            external_transfer.status = "Approved"

    else:

        current_balance = float(
            customer.account_balance or 0
        )

        if approval.direction == "Debit":

            if amount > current_balance:
                flash(
                    "The customer no longer has sufficient available balance.",
                    "error"
                )
                return redirect(
                    url_for(
                        "admin_review_payment",
                        approval_id=approval.id
                    )
                )

            new_balance = current_balance - amount
            customer.account_balance = new_balance

            transaction = Transaction(
                transaction_reference=generate_transaction_reference(),
                customer_id=customer.customer_id,
                transaction_type=approval.payment_type,
                direction="Debit",
                amount=amount,
                balance_after=new_balance,
                description=approval.description,
                counterparty=approval.counterparty,
                status="Completed"
            )

            db.session.add(transaction)
            transactions_to_notify.append(transaction)

        elif approval.direction == "Credit":

            new_balance = current_balance + amount
            customer.account_balance = new_balance

            transaction = Transaction(
                transaction_reference=generate_transaction_reference(),
                customer_id=customer.customer_id,
                transaction_type=approval.payment_type,
                direction="Credit",
                amount=amount,
                balance_after=new_balance,
                description=approval.description,
                counterparty=approval.counterparty,
                status="Completed",
                sender_name=approval.sender_name,
                sender_account_number=approval.sender_account_number,
                sender_bank=approval.sender_bank,
                sender_country=approval.sender_country
            )

            db.session.add(transaction)
            transactions_to_notify.append(transaction)

        else:
            flash(
                "Unsupported payment direction.",
                "error"
            )
            return redirect(
                url_for(
                    "admin_review_payment",
                    approval_id=approval.id
                )
            )

    approval.status = "Approved"
    approval.reviewed_at = datetime.utcnow()
    approval.reviewed_by = admin.username

    if approval.payment_type == "Bank Transfer" and approval.recipient_customer_id and recipient is not None:
        create_customer_notification(
            customer.customer_id,
            "Bank transfer completed",
            f"Your transfer of £{amount:,.2f} to {recipient.full_name} has been approved and completed.",
            notification_type="Transaction",
            commit=False,
        )
        create_customer_notification(
            recipient.customer_id,
            "Money received",
            f"You received £{amount:,.2f} from {customer.full_name}. The transfer has been completed.",
            notification_type="Transaction",
            commit=False,
        )
    elif approval.direction == "Credit":
        sender_label = approval.sender_name or approval.counterparty or "the sender"
        create_customer_notification(
            customer.customer_id,
            "Money received",
            f"A credit of £{amount:,.2f} from {sender_label} has been posted to your account.",
            notification_type="Transaction",
            commit=False,
        )
    else:
        create_customer_notification(
            customer.customer_id,
            "Payment completed",
            f"Your {approval.payment_type.lower()} of £{amount:,.2f} has been approved and processed.",
            notification_type="Transaction",
            commit=False,
        )

    db.session.commit()

    if not send_payment_status_email(customer, approval, event="approved"):
        app.logger.warning(
            "Payment approval email could not be sent for reference %s",
            approval.payment_reference,
        )

    # Send a branded approval-status notification to the external recipient.
    # Approval in this application does not itself confirm an external bank credit.
    if approval.payment_type == "International Transfer":
        external_transfer = None
        if approval.original_transaction_reference:
            external_transfer = ExternalTransfer.query.filter_by(
                transaction_reference=approval.original_transaction_reference
            ).first()

        if external_transfer and external_transfer.recipient_email:
            approval_email_sent = send_branded_recipient_email(
                recipient_email=external_transfer.recipient_email,
                recipient_name=external_transfer.recipient_name,
                subject="International Transfer Approved",
                eyebrow="Transfer Update",
                heading="International Transfer Approved",
                message_text=(
                    "The international transfer request addressed to you "
                    "has been approved by fairmontbank and is proceeding to the next stage of processing..\n\n"
                    "Please allow a few business days for the funds to be processed "
                    "and reflected in the beneficiary’s account, depending on the participating banks and destination.."
                ),   
                details=[
                    ("Transfer type", "International Transfer"),
                    (
                        "Amount",
                        f"{external_transfer.amount:,.2f} "
                        f"{external_transfer.currency}",
                    ),
                    ("Reference", external_transfer.transaction_reference),
                    ("Sending bank", external_transfer.bank_name),
                    ("Country", external_transfer.country),
                    ("Status", "Approved"),
                ],
            )
            if not approval_email_sent:
                app.logger.warning(
                    "Recipient approval email failed for reference %s",
                    external_transfer.transaction_reference,
                )

    for recorded_transaction in transactions_to_notify:
        transaction_customer = Customer.query.filter_by(
            customer_id=recorded_transaction.customer_id
        ).first()
        if not send_transaction_alert(transaction_customer, recorded_transaction):
            app.logger.info(
                "Transaction alert not sent for reference %s",
                recorded_transaction.transaction_reference,
            )

    flash(
        "Payment approved successfully and the account balance has been updated.",
        "success"
    )

    return redirect(
        url_for(
            "admin_payment_approvals",
            status="Pending Approval"
        )
    )


@app.route(
    "/admin/payment-approval/<int:approval_id>/reject",
    methods=["POST"]
)
def admin_reject_payment(approval_id):

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    approval = db.session.get(
        PaymentApproval,
        approval_id
    )

    if approval is None:
        return redirect(url_for("admin_payment_approvals"))

    if approval.status != "Pending Approval":
        flash(
            "This payment has already been reviewed.",
            "error"
        )
        return redirect(
            url_for(
                "admin_payment_approvals",
                status="Pending Approval"
            )
        )

    approval.status = "Rejected"
    approval.reviewed_at = datetime.utcnow()
    approval.reviewed_by = admin.username
    approval.rejection_reason = (
        request.form.get(
            "rejection_reason",
            ""
        ).strip()
        or "Payment rejected by Fairmont Bank Support."
    )

    db.session.commit()

    customer = Customer.query.filter_by(
        customer_id=approval.customer_id
    ).first()
    if not send_payment_status_email(customer, approval, event="rejected"):
        app.logger.warning(
            "Payment rejection email could not be sent for reference %s",
            approval.payment_reference,
        )

    flash(
        "Payment request rejected. No customer balance was changed.",
        "success"
    )

    return redirect(
        url_for(
            "admin_payment_approvals",
            status="Pending Approval"
        )
    )

def admin_incoming_payment():

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        return redirect(url_for("admin_login"))

    customers = (
        Customer.query
        .order_by(Customer.full_name.asc())
        .all()
    )

    customer_data = [
        {
            "id": customer.id,
            "customer_id": customer.customer_id,
            "account_number": customer.account_number or "",
            "full_name": customer.full_name or "",
            "balance": float(customer.account_balance or 0)
        }
        for customer in customers
    ]

    form_data = (
        request.form.to_dict()
        if request.method == "POST"
        else {}
    )

    if request.method == "POST":

        receiver_customer_id = (
            request.form.get(
                "receiver_customer_id",
                ""
            ).strip()
        )

        sender_name = (
            request.form.get(
                "sender_name",
                ""
            ).strip()
        )

        sender_account_number = (
            request.form.get(
                "sender_account_number",
                ""
            ).strip()
        )

        sender_bank = (
            request.form.get(
                "sender_bank",
                ""
            ).strip()
        )

        sender_country = (
            request.form.get(
                "sender_country",
                ""
            ).strip()
        )

        payment_reference = (
            request.form.get(
                "payment_reference",
                ""
            ).strip()
        )

        description = (
            request.form.get(
                "description",
                ""
            ).strip()
        )

        amount_text = (
            request.form.get(
                "amount",
                ""
            ).strip()
        )

        if not receiver_customer_id:
            flash(
                "Please select the receiving Fairmont customer.",
                "error"
            )

            return render_template(
                "admin_incoming_payment.html",
                admin=admin,
                customers=customers,
                customer_data=customer_data,
                form_data=form_data
            )

        try:
            receiver_id = int(receiver_customer_id)
        except (TypeError, ValueError):

            flash(
                "Invalid receiving customer selection.",
                "error"
            )

            return render_template(
                "admin_incoming_payment.html",
                admin=admin,
                customers=customers,
                customer_data=customer_data,
                form_data=form_data
            )

        receiver = db.session.get(
            Customer,
            receiver_id
        )

        if receiver is None:

            flash(
                "The selected receiving customer could not be found.",
                "error"
            )

            return render_template(
                "admin_incoming_payment.html",
                admin=admin,
                customers=customers,
                customer_data=customer_data,
                form_data=form_data
            )

        if receiver.account_status != "Active":

            flash(
                "The receiving customer account is not active.",
                "error"
            )

            return render_template(
                "admin_incoming_payment.html",
                admin=admin,
                customers=customers,
                customer_data=customer_data,
                form_data=form_data
            )

        required_fields = [
            (
                sender_name,
                "Please enter the sender name."
            ),
            (
                sender_account_number,
                "Please enter the sender account number."
            ),
            (
                sender_bank,
                "Please enter the sender bank."
            ),
            (
                sender_country,
                "Please enter the sender country."
            ),
            (
                payment_reference,
                "Please enter the payment reference."
            ),
            (
                description,
                "Please enter a payment description."
            ),
        ]

        for value, error_message in required_fields:

            if not value:

                flash(
                    error_message,
                    "error"
                )

                return render_template(
                    "admin_incoming_payment.html",
                    admin=admin,
                    customers=customers,
                    customer_data=customer_data,
                    form_data=form_data
                )

        try:
            amount = float(amount_text)
        except (TypeError, ValueError):
            amount = 0

        if amount <= 0:

            flash(
                "Payment amount must be greater than zero.",
                "error"
            )

            return render_template(
                "admin_incoming_payment.html",
                admin=admin,
                customers=customers,
                customer_data=customer_data,
                form_data=form_data
            )

        previous_balance = float(
            receiver.account_balance or 0
        )

        new_balance = previous_balance + amount

        posted_at = datetime.now().strftime(
            "%d %B %Y, %H:%M:%S"
        )

        transaction_reference = (
            generate_transaction_reference()
        )

        receiver.account_balance = new_balance

        transaction = Transaction(
            transaction_reference=transaction_reference,
            customer_id=receiver.customer_id,
            transaction_type="Payment Received",
            direction="Credit",
            amount=amount,
            balance_after=new_balance,
            description=description,
            counterparty=sender_name,
            status="Completed",
            sender_name=sender_name,
            sender_account_number=sender_account_number,
            sender_bank=sender_bank,
            sender_country=sender_country
        )

        db.session.add(transaction)

        create_customer_notification(
            receiver.customer_id,
            "Money received",
            f"A payment of £{amount:,.2f} from {sender_name} ({sender_bank}) has been credited to your account. Reference: {transaction_reference}.",
            notification_type="Transaction",
            commit=False,
        )

        db.session.commit()

        if not send_transaction_alert(receiver, transaction):
            app.logger.info(
                "Incoming credit alert not sent for reference %s",
                transaction_reference,
            )

        return render_template(
            "admin_incoming_payment_success.html",
            admin=admin,
            receiver=receiver,
            sender_name=sender_name,
            sender_account_number=sender_account_number,
            sender_bank=sender_bank,
            sender_country=sender_country,
            amount=amount,
            payment_reference=payment_reference,
            description=description,
            transaction_reference=transaction_reference,
            previous_balance=previous_balance,
            new_balance=new_balance,
            posted_at=posted_at
        )

    return render_template(
        "admin_incoming_payment.html",
        admin=admin,
        customers=customers,
        customer_data=customer_data,
        form_data=form_data
    )



# ============================================================
# ADMIN â€” CREATE CUSTOMER ACCOUNT
# ============================================================

@app.route("/admin/create-customer", methods=["GET", "POST"])
def admin_create_customer():

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if admin is None or not admin.is_active:
        session.pop("admin_id", None)
        return redirect(url_for("admin_login"))

    form_data = (
        request.form.to_dict()
        if request.method == "POST"
        else {}
    )

    if request.method == "POST":

        full_name = (
            request.form.get("full_name", "").strip()
        )

        email = (
            request.form.get("email", "").strip().lower()
        )

        phone = (
            request.form.get("phone", "").strip()
        )

        account_type = (
            request.form.get("account_type", "").strip().lower()
        )

        country = (
            request.form.get("country", "").strip()
        )

        password = request.form.get("password", "")

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        initial_funding_text = (
            request.form.get(
                "initial_funding",
                "0"
            ).strip()
        )

        funding_reference = (
            request.form.get(
                "funding_reference",
                ""
            ).strip()
        )

        funding_description = (
            request.form.get(
                "funding_description",
                ""
            ).strip()
        )

        if not full_name:
            flash(
                "Please enter the customer's full name.",
                "error"
            )

            return render_template(
                "admin_create_customer.html",
                admin=admin,
                form_data=form_data
            )

        if not email:
            flash(
                "Please enter the customer's email address.",
                "error"
            )

            return render_template(
                "admin_create_customer.html",
                admin=admin,
                form_data=form_data
            )

        if not phone:
            flash(
                "Please enter the customer's phone number.",
                "error"
            )

            return render_template(
                "admin_create_customer.html",
                admin=admin,
                form_data=form_data
            )

        if account_type not in {"savings", "current"}:
            flash(
                "Please select a valid account type.",
                "error"
            )

            return render_template(
                "admin_create_customer.html",
                admin=admin,
                form_data=form_data
            )

        if not country:
            flash(
                "Please enter the customer's country.",
                "error"
            )

            return render_template(
                "admin_create_customer.html",
                admin=admin,
                form_data=form_data
            )

        if len(password) < 6:
            flash(
                "The initial password must contain at least 6 characters.",
                "error"
            )

            return render_template(
                "admin_create_customer.html",
                admin=admin,
                form_data=form_data
            )

        if password != confirm_password:
            flash(
                "The password confirmation does not match.",
                "error"
            )

            return render_template(
                "admin_create_customer.html",
                admin=admin,
                form_data=form_data
            )

        existing_email = Customer.query.filter_by(
            email=email
        ).first()

        if existing_email:
            flash(
                "A customer with that email address already exists.",
                "error"
            )

            return render_template(
                "admin_create_customer.html",
                admin=admin,
                form_data=form_data
            )

        existing_phone = Customer.query.filter_by(
            phone=phone
        ).first()

        if existing_phone:
            flash(
                "A customer with that phone number already exists.",
                "error"
            )

            return render_template(
                "admin_create_customer.html",
                admin=admin,
                form_data=form_data
            )

        try:
            initial_funding = float(
                initial_funding_text or "0"
            )
        except (TypeError, ValueError):

            flash(
                "Initial funding amount is not valid.",
                "error"
            )

            return render_template(
                "admin_create_customer.html",
                admin=admin,
                form_data=form_data
            )

        if initial_funding < 0:

            flash(
                "Initial funding cannot be negative.",
                "error"
            )

            return render_template(
                "admin_create_customer.html",
                admin=admin,
                form_data=form_data
            )

        if initial_funding > 0 and not funding_description:
            funding_description = "Initial account funding"

        # Generate a unique Fairmont Customer ID.
        customer_id = generate_customer_id()

        # Generate a unique 10-digit account number.
        account_number = generate_account_number()

        customer = Customer(
            customer_id=customer_id,
            account_number=account_number,
            full_name=full_name,
            email=email,
            phone=phone,
            account_type=account_type,
            country=country,
            password_hash=generate_password_hash(password),
            account_status="Active",
            account_balance=initial_funding
        )

        db.session.add(customer)

        db.session.flush()

        # Create the initial funding transaction only when
        # an amount greater than zero was provided.
        if initial_funding > 0:

            transaction_reference = (
                generate_transaction_reference()
            )

            transaction = Transaction(
                transaction_reference=transaction_reference,
                customer_id=customer.customer_id,
                transaction_type="Account Funding",
                direction="Credit",
                amount=initial_funding,
                balance_after=initial_funding,
                description=(
                    funding_description
                    or "Initial account funding"
                ),
                counterparty="Fairmont Bank",
                status="Completed",
                sender_name="Fairmont Bank",
                sender_account_number="",
                sender_bank="Fairmont Bank",
                sender_country="United Kingdom"
            )

            db.session.add(transaction)

        db.session.commit()

        if not send_branded_customer_email(
            customer,
            "Your Fairmont Bank Account Is Ready",
            "Account Setup",
            "Your Account Record Has Been Created",
            (
                "An account record has been created for you in the Fairmont Bank "
                "software. Use the customer reference provided by "
                "the administrator to access the bank account."
            ),
            [
                ("Customer reference", customer.customer_id),
                ("Account type", customer.account_type),
                ("Account status", customer.account_status),
            ],
        ):
            app.logger.warning(
                "Account setup email could not be sent for customer %s",
                customer.customer_id,
            )

        if initial_funding > 0:
            initial_transaction = Transaction.query.filter_by(
                transaction_reference=transaction_reference
            ).first()
            if initial_transaction is not None:
                send_transaction_alert(customer, initial_transaction)

        return render_template(
            "admin_create_customer_success.html",
            admin=admin,
            customer=customer,
            initial_funding=initial_funding,
            funding_reference=funding_reference,
            funding_description=funding_description,
            transaction_reference=(
                transaction_reference
                if initial_funding > 0
                else None
            )
        )

    return render_template(
        "admin_create_customer.html",
        admin=admin,
        form_data=form_data
    )



@app.route("/admin/fund-customer", methods=["GET", "POST"])
def admin_fund_customer():
    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(AdminUser, admin_id)

    if not admin or not admin.is_active:
        session.pop("admin_id", None)
        return redirect(url_for("admin_login"))

    customers = Customer.query.order_by(Customer.full_name.asc()).all()

    if request.method == "POST":
        receiver_customer_id = request.form.get(
            "customer_id",
            ""
        ).strip()

        amount_text = request.form.get(
            "amount",
            ""
        ).strip()

        funding_reference = request.form.get(
            "funding_reference",
            ""
        ).strip()

        funding_description = request.form.get(
            "funding_description",
            ""
        ).strip()

        if not receiver_customer_id:
            flash("Please select a customer.", "error")

            return render_template(
                "admin_fund_customer.html",
                admin=admin,
                customers=customers
            )

        customer = Customer.query.filter_by(
            customer_id=receiver_customer_id
        ).first()

        if not customer:
            flash("The selected customer could not be found.", "error")

            return render_template(
                "admin_fund_customer.html",
                admin=admin,
                customers=customers
            )

        if customer.account_status != "Active":
            flash(
                "Funds can only be added to an active customer account.",
                "error"
            )

            return render_template(
                "admin_fund_customer.html",
                admin=admin,
                customers=customers
            )

        try:
            amount = float(amount_text)
        except (TypeError, ValueError):
            amount = 0

        if amount <= 0:
            flash(
                "Funding amount must be greater than zero.",
                "error"
            )

            return render_template(
                "admin_fund_customer.html",
                admin=admin,
                customers=customers
            )

        current_balance = float(
            customer.account_balance or 0
        )

        new_balance = current_balance + amount

        transaction_reference = generate_transaction_reference()

        description = (
            funding_description
            if funding_description
            else "Account Funding"
        )

        if funding_reference:
            description = (
                f"{description} "
                f"(Reference: {funding_reference})"
            )

        customer.account_balance = new_balance

        transaction = Transaction(
            transaction_reference=transaction_reference,
            customer_id=customer.customer_id,
            transaction_type="Account Funding",
            direction="Credit",
            amount=amount,
            balance_after=new_balance,
            description=description,
            counterparty="Fairmont Bank",
            status="Completed",
            sender_name="Fairmont Bank",
            sender_account_number="",
            sender_bank="Fairmont Bank",
            sender_country="United Kingdom"
        )

        db.session.add(transaction)
        db.session.commit()

        if not send_transaction_alert(customer, transaction):
            app.logger.info(
                "Account funding alert not sent for reference %s",
                transaction_reference,
            )

        return render_template(
            "admin_fund_customer_success.html",
            admin=admin,
            customer=customer,
            amount=amount,
            previous_balance=current_balance,
            new_balance=new_balance,
            funding_reference=funding_reference,
            funding_description=funding_description,
            transaction_reference=transaction_reference
        )

    return render_template(
        "admin_fund_customer.html",
        admin=admin,
        customers=customers
    )


# FAIRMont_ADMIN_INCOMING_ENDPOINT_FIX
#
# Explicitly register the existing admin incoming-payment function
# under the endpoint name used by admin_dashboard.html.
#
# This repairs the endpoint without changing the existing payment
# processing logic.

if "admin_incoming_payment" not in app.view_functions:

    app.add_url_rule(
        "/admin/incoming-payment",
        endpoint="admin_incoming_payment",
        view_func=admin_incoming_payment,
        methods=["GET", "POST"]
    )


def ensure_bank_invoice_schema():
    """Safely add invoice columns that may be missing from an older SQLite table.

    SQLite/SQLAlchemy create_all() does not alter an existing table, so this
    small idempotent migration preserves existing invoice records.
    """
    from sqlalchemy import inspect, text

    db.create_all()
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if "bank_invoices" not in tables:
        return

    existing = {col["name"] for col in inspector.get_columns("bank_invoices")}

    optional_columns = {
        "payment_method": "VARCHAR(80)",
        "payment_reference": "VARCHAR(100)",
        "billing_note": "TEXT",
        "created_by": "VARCHAR(80)",
        "paid_at": "DATETIME",
    }

    with db.engine.begin() as conn:
        for column_name, sql_type in optional_columns.items():
            if column_name not in existing:
                conn.execute(
                    text(
                        f'ALTER TABLE bank_invoices ADD COLUMN "{column_name}" {sql_type}'
                    )
                )


def ensure_payment_approvals_schema():
    """Add newer payment_approvals columns to existing PostgreSQL databases."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "payment_approvals" not in inspector.get_table_names():
        # db.create_all() below creates the complete table when it is absent.
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("payment_approvals")
    }

    # Use explicit PostgreSQL/SQLite-compatible column types. Defaults are
    # included where required so existing rows remain valid after migration.
    missing_columns = {
        "recipient_customer_id": "VARCHAR(20)",
        "recipient_name": "VARCHAR(150)",
        "recipient_email": "VARCHAR(254) NOT NULL DEFAULT ''",
        "recipient_account_number": "VARCHAR(50)",
        "original_transaction_reference": "VARCHAR(40)",
        "tcc_status": "VARCHAR(30) NOT NULL DEFAULT 'Not Required'",
        "tcc_code": "VARCHAR(6)",
        "tcc_generated_at": "TIMESTAMP",
        "tcc_expires_at": "TIMESTAMP",
        "tcc_verified_at": "TIMESTAMP",
        "tcc_attempts": "INTEGER NOT NULL DEFAULT 0",
    }

    with db.engine.begin() as connection:
        for column_name, sql_definition in missing_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(
                    f'ALTER TABLE payment_approvals ADD COLUMN "{column_name}" {sql_definition}'
                ))
                app.logger.info(
                    "Database migration added payment_approvals.%s", column_name
                )


def ensure_external_transfer_schema():
    """Add columns introduced after the external_transfer table was created."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "external_transfer" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("external_transfer")
    }

    # Existing rows receive an empty email value. This is an additive migration
    # and does not delete or rewrite existing transfer records.
    missing_columns = {
        "recipient_email": "VARCHAR(254) NOT NULL DEFAULT ''",
    }

    with db.engine.begin() as connection:
        for column_name, sql_definition in missing_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(
                    f'ALTER TABLE external_transfer ADD COLUMN "{column_name}" {sql_definition}'
                ))
                app.logger.info(
                    "Database migration added external_transfer.%s", column_name
                )


# Initialize missing database tables after every SQLAlchemy model has been
# declared. Render starts this application with Gunicorn, which imports app.py
# without executing the __main__ block. create_all() creates missing tables
# and does not delete existing tables or records. It does not alter existing
# table definitions; use explicit migrations for column changes.
try:
    with app.app_context():
        db.create_all()
        ensure_payment_approvals_schema()
        ensure_external_transfer_schema()
        from sqlalchemy import inspect
        _database_tables = set(inspect(db.engine).get_table_names())
        if "transactions" not in _database_tables:
            raise RuntimeError(
                "Database initialization finished but the transactions table is missing. "
                "Check DATABASE_URL and database permissions."
            )
        app.logger.info(
            "Database initialization complete; transactions table is available."
        )
except Exception:
    app.logger.exception("Database initialization failed during application startup.")
    raise


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_bank_invoice_schema()
        ensure_account_preference_columns()
        ensure_virtual_card_security_code_column()
        ensure_live_chat_guest_column()
        repair_payment_approvals_sequence()


    with app.app_context():
        db.create_all()

    app.run(
        debug=True
    )




