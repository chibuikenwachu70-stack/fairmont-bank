import os
import re
import shutil
from datetime import datetime

APP = "app.py"
PROFILE = os.path.join("templates", "admin_customer_profile.html")
LOGIN_OTP = os.path.join("templates", "login_otp_verify.html")
ADMIN_DASH = os.path.join("templates", "admin_dashboard.html")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

print("=" * 70)
print(" FAIRMONT BANK - ADMIN CONTROLLED CUSTOMER OTP")
print("=" * 70)

# ---------------------------------------------------------
# BACKUPS
# ---------------------------------------------------------

for filename in [APP, PROFILE, LOGIN_OTP, ADMIN_DASH]:
    if os.path.exists(filename):
        backup = f"{filename}.backup_admin_otp_{timestamp}"
        shutil.copy2(filename, backup)
        print(f"Backup: {backup}")

# ---------------------------------------------------------
# READ APP
# ---------------------------------------------------------

with open(APP, "r", encoding="utf-8") as f:
    app = f.read()

# ---------------------------------------------------------
# CHECK REQUIRED DATABASE STRUCTURES
# ---------------------------------------------------------

required = [
    "class CustomerLoginOTP",
    "login_otp_enabled",
]

for item in required:
    if item not in app:
        raise SystemExit(
            f"\nERROR: Required existing feature not found: {item}\n"
            "No changes were made."
        )

print("\nExisting OTP database structures found.")

# ---------------------------------------------------------
# MAKE SURE REQUIRED IMPORTS EXIST
# ---------------------------------------------------------

if "import secrets" not in app:
    app = "import secrets\n" + app

if "from datetime import" in app and "timedelta" not in app.split("from datetime import", 1)[1].split("\n", 1)[0]:
    app = re.sub(
        r"from datetime import ([^\n]+)",
        lambda m: (
            m.group(0)
            if "timedelta" in m.group(1)
            else "from datetime import " + m.group(1).rstrip() + ", timedelta"
        ),
        app,
        count=1
    )

# ---------------------------------------------------------
# REMOVE ANY OLD ADMIN OTP ROUTES WE ARE REPLACING
# ---------------------------------------------------------

def remove_function(app_text, function_name):
    pattern = re.compile(
        r'\n@app\.route\([^\n]+\)\n'
        r'def ' + re.escape(function_name) + r'\([^\n]*\):.*?'
        r'(?=\n@app\.route|\n# ={5,}|\Z)',
        re.S
    )

    new_text, count = pattern.subn("", app_text)

    if count:
        print(f"Removed old {function_name} route.")
    return new_text


app = remove_function(app, "admin_login_otp_requests")
app = remove_function(app, "admin_mark_login_otp_used")

# ---------------------------------------------------------
# ADD ADMIN OTP MANAGEMENT ROUTES
# ---------------------------------------------------------

admin_otp_routes = r'''

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
        return redirect(url_for("admin_login"))

    otp_requests = (
        CustomerLoginOTP.query
        .filter_by(used=False)
        .order_by(CustomerLoginOTP.created_at.desc())
        .all()
    )

    active_requests = []

    now = datetime.now(timezone.utc)

    for otp in otp_requests:

        if otp.expires_at and now > otp.expires_at:
            otp.used = True
            continue

        customer = db.session.get(Customer, otp.customer_id)

        if customer and customer.login_otp_enabled:
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

'''

# Insert before admin dashboard route if possible.
marker = '\ndef admin_dashboard():'

if "def admin_toggle_customer_login_otp" not in app:
    if marker in app:
        app = app.replace(
            marker,
            admin_otp_routes + marker,
            1
        )
    else:
        app += admin_otp_routes

    print("Admin OTP management routes added.")

# ---------------------------------------------------------
# MODIFY CUSTOMER LOGIN
# ---------------------------------------------------------

login_pattern = re.compile(
    r'(@app\.route\("/login", methods=\["GET", "POST"\]\)\n'
    r'def login\(\):.*?)(?=\n# =========================================================\n# OPEN ACCOUNT)',
    re.S
)

match = login_pattern.search(app)

if not match:
    raise SystemExit(
        "\nERROR: Customer login function could not be located.\n"
        "No login changes were made."
    )

login_block = match.group(1)

# Prevent duplicate insertion
otp_login_marker = "# ADMIN CONTROLLED OTP LOGIN"

if otp_login_marker not in login_block:

    target = '''        if not check_password_hash(
            customer.password_hash,
            password
        ):

            return render_template(
                "login.html",
                error="Invalid Customer ID or password."
            )
'''

    replacement = target + r'''
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
'''

    if target not in login_block:
        raise SystemExit(
            "\nERROR: Login password verification block was not found.\n"
            "No login changes were made."
        )

    login_block = login_block.replace(
        target,
        replacement,
        1
    )

    app = app[:match.start(1)] + login_block + app[match.end(1):]

    print("Customer login updated for admin-controlled OTP.")

# ---------------------------------------------------------
# RESTORE OTP VERIFICATION ROUTE
# ---------------------------------------------------------

if 'def verify_login_otp()' not in app:

    verify_route = r'''

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

'''

    marker = '\n# =========================================================\n# OPEN ACCOUNT'

    if marker in app:
        app = app.replace(
            marker,
            verify_route + marker,
            1
        )
    else:
        app += verify_route

    print("OTP verification route restored.")

# ---------------------------------------------------------
# WRITE APP
# ---------------------------------------------------------

with open(APP, "w", encoding="utf-8") as f:
    f.write(app)

# ---------------------------------------------------------
# UPDATE ADMIN CUSTOMER PROFILE
# ---------------------------------------------------------

if os.path.exists(PROFILE):

    with open(PROFILE, "r", encoding="utf-8") as f:
        profile = f.read()

    if "admin_toggle_customer_login_otp" not in profile:

        anchor = """
        <div class="profile-detail-box">
            <span>Transaction Notifications</span>
"""

        otp_panel = r'''
        <div class="profile-detail-box">
            <span>Customer Login OTP</span>

            <strong>
                {% if customer.login_otp_enabled %}
                    Enabled
                {% else %}
                    Disabled
                {% endif %}
            </strong>

            <form
                method="POST"
                action="{{ url_for('admin_toggle_customer_login_otp', customer_id=customer.id) }}"
                style="margin-top: 10px;"
            >

                {% if customer.login_otp_enabled %}

                    <button
                        type="submit"
                        class="action"
                    >
                        Disable Login OTP
                    </button>

                {% else %}

                    <button
                        type="submit"
                        class="action"
                    >
                        Enable Login OTP
                    </button>

                {% endif %}

            </form>
        </div>

'''

        if anchor in profile:
            profile = profile.replace(
                anchor,
                otp_panel + anchor,
                1
            )

            with open(PROFILE, "w", encoding="utf-8") as f:
                f.write(profile)

            print("Admin customer profile OTP control added.")

# ---------------------------------------------------------
# UPDATE CUSTOMER OTP PAGE
# ---------------------------------------------------------

if os.path.exists(LOGIN_OTP):

    with open(LOGIN_OTP, "r", encoding="utf-8") as f:
        otp_page = f.read()

    # Replace common old delivery wording.
    replacements = {
        "verification code has been sent to your phone":
            "a verification code is required to complete your login",
        "A verification code has been sent to your phone.":
            "A verification code is required to complete your login. Please contact the bank administrator to obtain your verification code.",
        "OTP has been sent to your number":
            "A verification code is required. Please contact the bank administrator.",
        "OTP has been sent to your phone":
            "A verification code is required. Please contact the bank administrator.",
    }

    for old, new in replacements.items():
        otp_page = otp_page.replace(old, new)

    if "contact the bank administrator" not in otp_page.lower():

        otp_page = otp_page.replace(
            "Verification code",
            "Verification code",
            1
        )

    with open(LOGIN_OTP, "w", encoding="utf-8") as f:
        f.write(otp_page)

    print("Customer OTP wording checked.")

# ---------------------------------------------------------
# CREATE ADMIN OTP TEMPLATE IF MISSING
# ---------------------------------------------------------

ADMIN_OTP_TEMPLATE = os.path.join(
    "templates",
    "admin_login_otp_requests.html"
)

if not os.path.exists(ADMIN_OTP_TEMPLATE):

    html = r'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Login OTP Requests</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f5f7fa;
            margin: 0;
            padding: 40px;
        }

        .container {
            max-width: 1000px;
            margin: auto;
        }

        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 16px;
            box-shadow: 0 2px 10px rgba(0,0,0,.08);
        }

        .otp {
            font-size: 32px;
            font-weight: bold;
            letter-spacing: 6px;
            margin: 12px 0;
        }

        .customer {
            font-size: 18px;
            font-weight: bold;
        }

        button {
            padding: 10px 18px;
            border: 0;
            border-radius: 8px;
            cursor: pointer;
        }
    </style>
</head>

<body>

<div class="container">

    <h1>Login OTP Requests</h1>

    <p>
        Active customer login verification codes.
        Give the code to the customer who is completing their login.
    </p>

    {% if otp_requests %}

        {% for item in otp_requests %}

            <div class="card">

                <div class="customer">
                    {{ item.customer.full_name }}
                </div>

                <div>
                    Customer ID:
                    {{ item.customer.customer_id }}
                </div>

                <div class="otp">
                    {{ item.otp.otp_code }}
                </div>

                <div>
                    Expires:
                    {{ item.otp.expires_at }}
                </div>

                <form
                    method="POST"
                    action="{{ url_for('admin_mark_login_otp_used', otp_id=item.otp.id) }}"
                >
                    <button type="submit">
                        Mark Code Used
                    </button>
                </form>

            </div>

        {% endfor %}

    {% else %}

        <div class="card">
            No active login OTP requests.
        </div>

    {% endif %}

</div>

</body>
</html>
'''

    with open(ADMIN_OTP_TEMPLATE, "w", encoding="utf-8") as f:
        f.write(html)

    print("Admin OTP page created.")

# ---------------------------------------------------------
# ADMIN DASHBOARD LINK
# ---------------------------------------------------------

if os.path.exists(ADMIN_DASH):

    with open(ADMIN_DASH, "r", encoding="utf-8") as f:
        dashboard = f.read()

    if "admin_login_otp_requests" not in dashboard:

        link = r'''
        <a href="{{ url_for('admin_login_otp_requests') }}"
           class="nav-link">

            <span class="nav-icon">OTP</span>
            Login OTP Requests

        </a>

'''

        marker = '<div class="sidebar-bottom">'

        if marker in dashboard:
            dashboard = dashboard.replace(
                marker,
                link + marker,
                1
            )

            with open(ADMIN_DASH, "w", encoding="utf-8") as f:
                f.write(dashboard)

            print("Admin OTP requests link added.")

print("\n" + "=" * 70)
print(" INSTALLATION COMPLETE")
print("=" * 70)
print()
print("Admin controls:")
print("  - Enable OTP for individual customers")
print("  - Disable OTP for individual customers")
print("  - View active OTP codes")
print("  - Mark OTP codes as used")
print()
print("Customer controls:")
print("  - No OTP setting")
print("  - No OTP delivery setting")
print("  - OTP required only when admin enables it")
print()
print("OTP lifetime: 10 minutes")
print()
print("Backups were created before modifications.")
print()
print("NEXT STEP:")
print("Restart Flask and test an OTP-enabled customer.")
print("=" * 70)