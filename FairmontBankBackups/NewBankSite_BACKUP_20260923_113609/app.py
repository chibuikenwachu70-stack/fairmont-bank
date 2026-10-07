from flask import Flask, render_template, request, session, redirect, url_for, url_for
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


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_account_preference_columns()


    with app.app_context():
        db.create_all()

    app.run(
        debug=True
    )

