from flask import Flask, render_template, request, session, redirect, url_for, url_for, flash
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
from datetime import datetime


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

app.config["SQLALCHEMY_DATABASE_URI"] = (
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

        existing = Transaction.query.filter_by(
            transaction_reference=reference
        ).first()

        if existing is None:

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

            account_status="Active",

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

    return render_template(
        "dashboard.html",
        customer=customer,
        notification_unread_count=notification_unread_count
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
        flash("Please enter the recipient name.", "error")
        return redirect(url_for("send_money"))

    if not bank_name:
        flash("Please select a bank.", "error")
        return redirect(url_for("send_money"))

    if not re.fullmatch(r"\d{8}", account_number):
        flash("Account number must contain exactly 8 digits.", "error")
        return redirect(url_for("send_money"))

    if not re.fullmatch(r"\d{6}", sort_code):
        flash("Sort code must contain exactly 6 digits.", "error")
        return redirect(url_for("send_money"))

    try:
        amount = float(amount_text)
    except (TypeError, ValueError):
        flash("Please enter a valid amount.", "error")
        return redirect(url_for("send_money"))

    if amount <= 0:
        flash("Payment amount must be greater than zero.", "error")
        return redirect(url_for("send_money"))

    if amount > float(customer.account_balance or 0):
        flash("Insufficient available balance.", "error")
        return redirect(url_for("send_money"))

    bank = Bank.query.filter_by(
        name=bank_name,
        country="United Kingdom",
        active=True
    ).first()

    if not bank:
        flash("The selected UK bank is not available.", "error")
        return redirect(url_for("send_money"))

    # -----------------------------------------------------
    # FAIRMOINT INTERNAL ACCOUNT MATCH
    # -----------------------------------------------------

    recipient_customer = Customer.query.filter_by(
        account_number=account_number
    ).first()

    if recipient_customer and recipient_customer.customer_id == customer.customer_id:
        flash(
            "You cannot send a payment to your own account.",
            "error"
        )
        return redirect(url_for("send_money"))

    # -----------------------------------------------------
    # INTERNAL FAIRMONT TRANSFER
    # -----------------------------------------------------

    if recipient_customer:

        if str(recipient_customer.account_status).lower() != "active":
            flash(
                "The recipient account is not active.",
                "error"
            )
            return redirect(url_for("send_money"))

        customer.account_balance = (
            float(customer.account_balance or 0)
            - amount
        )

        recipient_customer.account_balance = (
            float(recipient_customer.account_balance or 0)
            + amount
        )

        reference_value = (
            reference
            if reference
            else "Bank payment"
        )

        sender_transaction = Transaction(
            transaction_reference=generate_transaction_reference(),
            customer_id=customer.customer_id,
            transaction_type="Bank Transfer",
            direction="Debit",
            amount=amount,
            balance_after=float(customer.account_balance),
            description=reference_value,
            counterparty=recipient_customer.full_name,
            status="Completed"
        )

        recipient_transaction = Transaction(
            transaction_reference=generate_transaction_reference(),
            customer_id=recipient_customer.customer_id,
            transaction_type="Bank Transfer",
            direction="Credit",
            amount=amount,
            balance_after=float(recipient_customer.account_balance),
            description=reference_value,
            counterparty=customer.full_name,
            status="Completed"
        )

        db.session.add(sender_transaction)
        db.session.add(recipient_transaction)

        db.session.commit()

        return render_template(
            "transfer_confirmation.html",
            customer=customer,
            amount=amount,
            recipient_name=recipient_customer.full_name,
            bank_name=bank_name,
            account_number=account_number,
            sort_code=sort_code,
            reference=reference,
            status="Completed"
        )

    # -----------------------------------------------------
    # EXTERNAL UK BANK PAYMENT
    # -----------------------------------------------------

    transfer_reference = generate_transaction_reference()

    external_transfer = ExternalTransfer(
        transaction_reference=transfer_reference,
        customer_id=customer.customer_id,
        transfer_type="UK Bank Payment",
        bank_name=bank_name,
        recipient_name=recipient_name,
        account_number=account_number,
        sort_code=sort_code,
        country="United Kingdom",
        currency="GBP",
        amount=amount,
        fee=0.0,
        reference=reference,
        status="Pending"
    )

    db.session.add(external_transfer)
    db.session.commit()

    return render_template(
        "transfer_confirmation.html",
        customer=customer,
        amount=amount,
        recipient_name=recipient_name,
        bank_name=bank_name,
        account_number=account_number,
        sort_code=sort_code,
        reference=reference,
        status="Pending"
    )



# ============================================================
# INTERNATIONAL TRANSFER
# ============================================================

@app.route("/international-transfer", methods=["GET", "POST"])
@login_required
def international_transfer():
    if request.method == "POST":
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
            flash("Please complete all required international transfer fields.", "error")
            return render_template(
                "international_transfer.html",
                customer=current_user
            )

        try:
            amount = float(amount_text)
        except (TypeError, ValueError):
            flash("Please enter a valid transfer amount.", "error")
            return render_template(
                "international_transfer.html",
                customer=current_user
            )

        if amount <= 0:
            flash("Transfer amount must be greater than zero.", "error")
            return render_template(
                "international_transfer.html",
                customer=current_user
            )

        current_balance = float(current_user.account_balance or 0)

        if amount > current_balance:
            flash("The transfer amount exceeds your available balance.", "error")
            return render_template(
                "international_transfer.html",
                customer=current_user
            )

        # --------------------------------------------------------
        # Create the ExternalTransfer without debiting the account.
        # International transfers remain Pending until processed.
        # --------------------------------------------------------

        transfer = ExternalTransfer()

        transfer_values = {
            "customer_id": current_user.id,
            "recipient_name": recipient_name,
            "recipient_address": recipient_address,
            "country": country,
            "bank_name": bank_name,
            "account_number": account_number,
            "swift_bic": swift_bic,
            "local_bank_code": local_bank_code,
            "currency": currency,
            "amount": amount,
            "reference": reference or "International Transfer",
            "status": "Pending",
        }

        for field_name, field_value in transfer_values.items():
            if hasattr(transfer, field_name):
                setattr(transfer, field_name, field_value)

        db.session.add(transfer)
        db.session.commit()

        transfer_reference = None

        for possible_field in [
            "reference",
            "transfer_reference",
            "transaction_reference"
        ]:
            if hasattr(transfer, possible_field):
                possible_value = getattr(transfer, possible_field, None)
                if possible_value:
                    transfer_reference = possible_value
                    break

        if not transfer_reference:
            transfer_reference = reference or "Pending International Transfer"

        return render_template(
            "international_confirmation.html",
            customer=current_user,
            transfer=transfer,
            transfer_reference=transfer_reference
        )

    return render_template(
        "international_transfer.html",
        customer=current_user
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
                "Payment amount must be greater than £0.00."
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

    transaction_reference = generate_transaction_reference()

    customer.account_balance = (
        float(customer.account_balance or 0)
        - amount
    )

    description = (
        f"{bill_category} payment"
    )

    counterparty = provider

    transaction = Transaction(

        transaction_reference=transaction_reference,

        customer_id=customer.customer_id,

        transaction_type="Bill Payment",

        direction="Debit",

        amount=amount,

        balance_after=float(
            customer.account_balance
        ),

        description=description,

        counterparty=counterparty,

        status="Completed"
    )

    db.session.add(transaction)

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        return render_template(
            "pay_bills.html",
            customer=customer,
            errors=[
                "The payment could not be completed. Please try again."
            ],
            form=request.form
        )

    return render_template(
        "bill_payment_confirmation.html",
        customer=customer,
        transaction=transaction,
        bill_category=bill_category,
        provider=provider,
        account_reference=account_reference,
        payment_reference=payment_reference
    )



# ============================================================
# ELECTRIC BILLS
# ============================================================

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

    if amount > float(customer.account_balance):
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

    new_balance = float(customer.account_balance) - amount

    transaction_reference = generate_transaction_reference()

    customer.account_balance = new_balance

    transaction = Transaction(
        transaction_reference=transaction_reference,
        customer_id=customer.id,
        transaction_type="Electricity Bill",
        direction="Debit",
        amount=amount,
        balance_after=new_balance,
        description="Electricity bill payment",
        counterparty=provider,
        status="Completed"
    )

    db.session.add(transaction)
    db.session.commit()

    return render_template(
        "electric_bill_confirmation.html",
        customer=customer,
        provider=provider,
        meter_number=meter_number,
        amount=amount,
        payment_reference=payment_reference,
        transaction_reference=transaction_reference,
        new_balance=new_balance
    )


# ============================================================


@app.route("/airtime", methods=["GET", "POST"])
@login_required
def airtime():
    customer = current_user

    if request.method == "GET":
        return render_template(
            "airtime.html",
            customer=customer
        )

    provider = request.form.get("provider", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    amount_text = request.form.get("amount", "").strip()
    payment_reference = request.form.get("payment_reference", "").strip()

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

    if amount > float(customer.account_balance):
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

    new_balance = float(customer.account_balance) - amount
    transaction_reference = generate_transaction_reference()

    customer.account_balance = new_balance

    transaction = Transaction(
        transaction_reference=transaction_reference,
        customer_id=customer.id,
        transaction_type="Airtime Purchase",
        direction="Debit",
        amount=amount,
        balance_after=new_balance,
        description="Mobile airtime purchase",
        counterparty=provider,
        status="Completed"
    )

    db.session.add(transaction)
    db.session.commit()

    return render_template(
        "airtime_confirmation.html",
        customer=customer,
        provider=provider,
        phone_number=phone_number,
        amount=amount,
        payment_reference=payment_reference,
        transaction_reference=transaction_reference,
        new_balance=new_balance
    )

# START APPLICATION
# ============================================================


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

    provider = request.form.get("provider", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    bundle_name = request.form.get("bundle_name", "").strip()
    payment_reference = request.form.get("payment_reference", "").strip()

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

    if amount > float(customer.account_balance):
        errors.append("Insufficient balance for this data bundle purchase.")

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

    new_balance = float(customer.account_balance) - amount

    transaction_reference = generate_transaction_reference()

    customer.account_balance = new_balance

    transaction = Transaction(
        transaction_reference=transaction_reference,
        customer_id=customer.id,
        transaction_type="Data Bundle Purchase",
        direction="Debit",
        amount=amount,
        balance_after=new_balance,
        description=f"{bundle_name} mobile data bundle",
        counterparty=provider,
        status="Completed"
    )

    db.session.add(transaction)
    db.session.commit()

    return render_template(
        "data_bundle_confirmation.html",
        customer=customer,
        provider=provider,
        phone_number=phone_number,
        bundle_name=bundle_name,
        amount=amount,
        payment_reference=payment_reference,
        transaction_reference=transaction_reference,
        new_balance=new_balance
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

    provider = request.form.get("provider", "").strip()
    package_name = request.form.get("package_name", "").strip()
    account_reference = request.form.get("account_reference", "").strip()
    payment_reference = request.form.get("payment_reference", "").strip()

    errors = []

    if provider not in providers:
        errors.append("Please select a TV provider.")

    if not account_reference:
        errors.append("Please enter your TV account or customer number.")

    selected_package = None

    if provider in packages:
        for package in packages[provider]:
            if package["name"] == package_name:
                selected_package = package
                break

    if selected_package is None:
        errors.append("Please select a valid TV subscription package.")

    amount = selected_package["amount"] if selected_package else 0.0

    if amount > float(customer.account_balance):
        errors.append("Insufficient balance for this TV subscription payment.")

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

    new_balance = float(customer.account_balance) - amount

    transaction_reference = generate_transaction_reference()

    customer.account_balance = new_balance

    transaction = Transaction(
        transaction_reference=transaction_reference,
        customer_id=customer.id,
        transaction_type="TV Subscription",
        direction="Debit",
        amount=amount,
        balance_after=new_balance,
        description=f"{provider} - {package_name}",
        counterparty=provider,
        status="Completed"
    )

    db.session.add(transaction)
    db.session.commit()

    return render_template(
        "tv_subscription_confirmation.html",
        customer=customer,
        provider=provider,
        package_name=package_name,
        account_reference=account_reference,
        amount=amount,
        payment_reference=payment_reference,
        transaction_reference=transaction_reference,
        new_balance=new_balance
    )


@app.route("/settings/bank-statements-lock", methods=["GET", "POST"])
@login_required
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
        .filter_by(customer_id=customer.id)
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

    category = request.form.get("category", "").strip()
    merchant = request.form.get("merchant", "").strip()
    account_reference = request.form.get("account_reference", "").strip()
    amount_text = request.form.get("amount", "").strip()
    payment_reference = request.form.get("payment_reference", "").strip()

    errors = []

    if category not in lifestyle_categories:
        errors.append("Please select a lifestyle category.")

    if not merchant:
        errors.append("Please enter the merchant or service name.")

    if not account_reference:
        errors.append("Please enter the customer or order reference.")

    try:
        amount = float(amount_text)
    except (TypeError, ValueError):
        amount = 0

    if amount <= 0:
        errors.append("Please enter a valid payment amount.")

    if amount > float(customer.account_balance):
        errors.append("Insufficient balance for this lifestyle payment.")

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

    new_balance = float(customer.account_balance) - amount
    transaction_reference = generate_transaction_reference()

    customer.account_balance = new_balance

    transaction = Transaction(
        transaction_reference=transaction_reference,
        customer_id=customer.id,
        transaction_type="Lifestyle Payment",
        direction="Debit",
        amount=amount,
        balance_after=new_balance,
        description=f"{category} payment",
        counterparty=merchant,
        status="Completed"
    )

    db.session.add(transaction)
    db.session.commit()

    return render_template(
        "lifestyle_confirmation.html",
        customer=customer,
        category=category,
        merchant=merchant,
        account_reference=account_reference,
        amount=amount,
        payment_reference=payment_reference,
        transaction_reference=transaction_reference,
        new_balance=new_balance
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

    category = request.form.get("category", "").strip()
    provider = request.form.get("provider", "").strip()
    traveler_name = request.form.get("traveler_name", "").strip()
    booking_reference = request.form.get("booking_reference", "").strip()
    amount_text = request.form.get("amount", "").strip()
    payment_reference = request.form.get("payment_reference", "").strip()

    errors = []

    if category not in travel_categories:
        errors.append("Please select a travel service.")

    if not provider:
        errors.append("Please enter the airline, hotel, or travel provider.")

    if not traveler_name:
        errors.append("Please enter the traveler name.")

    if not booking_reference:
        errors.append("Please enter the booking or travel reference.")

    try:
        amount = float(amount_text)
    except (TypeError, ValueError):
        amount = 0

    if amount <= 0:
        errors.append("Please enter a valid payment amount.")

    if amount > float(customer.account_balance):
        errors.append("Insufficient balance for this travel payment.")

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

    new_balance = float(customer.account_balance) - amount
    transaction_reference = generate_transaction_reference()

    customer.account_balance = new_balance

    transaction = Transaction(
        transaction_reference=transaction_reference,
        customer_id=customer.id,
        transaction_type="Travel Payment",
        direction="Debit",
        amount=amount,
        balance_after=new_balance,
        description=f"{category} payment",
        counterparty=provider,
        status="Completed"
    )

    db.session.add(transaction)
    db.session.commit()

    return render_template(
        "flights_travel_confirmation.html",
        customer=customer,
        category=category,
        provider=provider,
        traveler_name=traveler_name,
        booking_reference=booking_reference,
        amount=amount,
        payment_reference=payment_reference,
        transaction_reference=transaction_reference,
        new_balance=new_balance
    )



# =========================================================
# FAIRMONT BANK CUSTOMER MESSAGES
# =========================================================

class BankMessage(db.Model):

    __tablename__ = "bank_messages"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    customer_id = db.Column(
        db.Integer,
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

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )




# =========================================================
# EMAIL THE BANK
# =========================================================

@app.route(
    "/email-bank",
    methods=["GET", "POST"]
)
@login_required
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
        .filter_by(customer_id=customer.id)
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
# ADMIN — POST INCOMING PAYMENT
# ============================================================

@app.route("/admin/incoming-payment", methods=["GET", "POST"])
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
# ADMIN — CREATE CUSTOMER ACCOUNT
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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_account_preference_columns()


    with app.app_context():
        db.create_all()

    app.run(
        debug=True
    )

