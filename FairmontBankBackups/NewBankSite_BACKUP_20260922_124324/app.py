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

    account_balance = db.Column(
        db.Float,
        nullable=False,
        default=0.0
    )




# =========================================================
# TRANSACTION MODEL
# =========================================================

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

        session.clear()

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

    transaction_list = (
        Transaction.query
        .filter_by(customer_id=customer.customer_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    return render_template(
        "transactions.html",
        customer=customer,
        transactions=transaction_list
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

    return render_template(
        "dashboard.html",
        customer=customer
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
        country="UK",
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
        country="UK",
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

if __name__ == "__main__":

    with app.app_context():

        db.create_all()

    app.run(
        debug=True
    )










