from flask import Flask, render_template, render_template_string, request, session, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_login import UserMixin
from flask_login import login_user
from flask_login import LoginManager
from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import string
import os
from datetime import datetime, timedelta
import re


app = Flask(__name__)

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
# Simulated local-app card record. It is not connected to a
# real card network and stores no CVV/PIN or real credentials.

class VirtualATMCard(db.Model):
    __tablename__ = "virtual_atm_cards"

    id = db.Column(db.Integer, primary_key=True)

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


class Transaction(db.Model):

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

    transaction_type = db.Column(
        db.String(40),
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

    balance_after = db.Column(
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
        default="Completed"
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


    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
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

        if customer.account_status != "Active":

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

        login_user(customer)

        session["customer_id"] = customer.customer_id

        next_url = request.form.get("next") or request.args.get("next")

        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)

        return redirect("/dashboard")

    return render_template(
        "login.html"
    )


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
            error="Please sign in to access your dashboard."
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

    return render_template(
        "dashboard.html",
        customer=customer,
        notification_unread_count=notification_unread_count,
        recent_transactions=recent_transactions,
        virtual_card=virtual_card
    )

# =========================================================
# CUSTOMER VIRTUAL ATM CARD
# =========================================================

@app.route("/virtual-card/apply", methods=["POST"])
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

    if existing_card is not None:
        flash(
            "You already have an active virtual ATM card.",
            "success"
        )
        return redirect(url_for("dashboard"))

    card = VirtualATMCard(
        customer_id=customer.customer_id,
        card_number=generate_virtual_card_number(),
        expiry_date=generate_virtual_card_expiry(),
        security_code=generate_virtual_card_security_code(),
        status="Active"
    )

    try:
        db.session.add(card)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(
            "The virtual card could not be created. Please try again.",
            "error"
        )
        return redirect(url_for("dashboard"))

    flash(
        "Your virtual ATM card has been created successfully.",
        "success"
    )

    return redirect(url_for("dashboard"))


@app.route("/virtual-card/review")
def virtual_card_review():
    customer_id = session.get("customer_id")

    if not customer_id:
        return redirect(url_for("login"))

    customer = Customer.query.filter_by(
        customer_id=customer_id
    ).first()

    if customer is None:
        session.clear()
        return redirect(url_for("login"))

    card = VirtualATMCard.query.filter_by(
        customer_id=customer.customer_id
    ).first()

    if card is None:
        flash(
            "You do not have a virtual ATM card yet.",
            "error"
        )
        return redirect(url_for("dashboard"))

    if not card.security_code:
        card.security_code = generate_virtual_card_security_code()
        db.session.commit()

    return render_template(
        "virtual_card_review.html",
        customer=customer,
        virtual_card=card
    )


@app.route("/my-profile")
def my_profile():

    customer_id = session.get("customer_id")

    if not customer_id:

        return render_template(
            "login.html",
            error="Please sign in to access your profile."
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

    return render_template(
        "my_profile.html",
        customer=customer
    )

@app.route("/logout")
def logout():

    session.clear()

    return render_template(
        "login.html"
    )


# =========================================================
# APPLICATION START
# =========================================================


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


@app.route("/send-money", methods=["GET", "POST"])
def send_money():

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
        db.session.commit()

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

    apply_tcc_requirement(
        customer,
        approval
    )

    db.session.add(approval)
    db.session.commit()

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

    try:
        db.session.add(transfer)
        db.session.add(approval)
        db.session.commit()
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

def bank_statements_lock_settings():
    customer = current_user

    if request.method == "POST":
        customer.bank_statements_locked = not customer.bank_statements_locked
        db.session.commit()

        return redirect(url_for("bank_statements_lock_settings"))

    return render_template(
        "bank_statements_lock.html",
        customer=customer
    )


@app.route("/bank-statements")
@login_required
def bank_statements():
    customer = current_user

    if customer.bank_statements_locked:
        return render_template(
            "bank_statements_locked.html",
            customer=customer
        )

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


@app.route("/settings/login-otp", methods=["GET", "POST"])
@login_required
def login_otp_settings():

    customer = current_user

    if request.method == "POST":

        otp_value = request.form.get(
            "login_otp_enabled",
            ""
        )

        customer.login_otp_enabled = (
            otp_value == "on"
        )

        db.session.commit()

        if customer.login_otp_enabled:

            flash(
                "Login OTP has been turned on.",
                "success"
            )

        else:

            flash(
                "Login OTP has been turned off.",
                "success"
            )

        return redirect(
            url_for("login_otp_settings")
        )

    return render_template(
        "login_otp.html",
        customer=customer
    )



# ============================================================
# FAIRmont BANK LIVE CHAT
# Customer Support Chat
# ============================================================

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

    db.session.commit()

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

        db.session.commit()

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


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_account_preference_columns()
        ensure_virtual_card_security_code_column()


    with app.app_context():
        db.create_all()

    app.run(
        debug=True
    )




