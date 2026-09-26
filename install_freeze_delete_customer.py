from pathlib import Path
from datetime import datetime
import shutil
import re

APP = Path("app.py")
TEMPLATE = Path("templates/admin_customer_profile.html")

print("=" * 70)
print(" FAIRMONT BANK - FREEZE / UNFREEZE + DELETE CUSTOMER")
print("=" * 70)

if not APP.exists():
    print("ERROR: app.py not found.")
    raise SystemExit(1)

if not TEMPLATE.exists():
    print("ERROR: admin_customer_profile.html not found.")
    raise SystemExit(1)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

app_backup = Path(
    f"app_backup_before_freeze_delete_{timestamp}.py"
)

template_backup = Path(
    f"admin_customer_profile_backup_before_freeze_delete_{timestamp}.html"
)

shutil.copy2(APP, app_backup)
shutil.copy2(TEMPLATE, template_backup)

print()
print("Backups created:")
print(" ", app_backup)
print(" ", template_backup)


# =========================================================
# APP.PY
# =========================================================

app_text = APP.read_text(encoding="utf-8")

# ---------------------------------------------------------
# FREEZE / UNFREEZE ROUTE
# ---------------------------------------------------------

if "def admin_toggle_customer_freeze(" not in app_text:

    freeze_route = r'''

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


'''

    # Put it immediately before admin_customer_profile.
    marker = '@app.route("/admin/customer/<int:customer_id>")'

    if marker in app_text:
        app_text = app_text.replace(
            marker,
            freeze_route + marker,
            1
        )
        print("Added Freeze / Unfreeze route.")
    else:
        print("ERROR: Could not locate admin_customer_profile route.")
        raise SystemExit(1)

else:
    print("Freeze / Unfreeze route already exists.")


# ---------------------------------------------------------
# DELETE CUSTOMER ROUTE
# ---------------------------------------------------------

if "def admin_delete_customer(" not in app_text:

    delete_route = r'''

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


'''

    marker = '@app.route("/admin/customer/<int:customer_id>")'

    if marker in app_text:
        app_text = app_text.replace(
            marker,
            delete_route + marker,
            1
        )
        print("Added Delete Customer route.")
    else:
        print("ERROR: Could not locate customer profile route.")
        raise SystemExit(1)

else:
    print("Delete Customer route already exists.")


APP.write_text(app_text, encoding="utf-8")


# =========================================================
# ADMIN CUSTOMER PROFILE
# =========================================================

template = TEMPLATE.read_text(encoding="utf-8")

# Replace the empty Locked/else placeholder.
old_block = r'''        {% if customer.account_status == "Locked" %}



        {% else %}



        {% endif %}'''

new_block = r'''        {% if customer.account_status == "Locked" %}

        <form method="POST"
              action="{{ url_for('admin_toggle_customer_freeze', customer_id=customer.id) }}">

            <button type="submit"
                    style="
                    padding:10px 16px;
                    border:0;
                    border-radius:8px;
                    background:#176b3a;
                    color:#fff;
                    font-weight:700;
                    cursor:pointer;
                    ">
                Unfreeze Customer Account
            </button>

        </form>

        {% else %}

        <form method="POST"
              action="{{ url_for('admin_toggle_customer_freeze', customer_id=customer.id) }}"
              onsubmit="return confirm('Freeze this customer account? The customer will not be able to sign in while the account is frozen.');">

            <button type="submit"
                    style="
                    padding:10px 16px;
                    border:0;
                    border-radius:8px;
                    background:#b36b00;
                    color:#fff;
                    font-weight:700;
                    cursor:pointer;
                    ">
                Freeze Customer Account
            </button>

        </form>

        {% endif %}

        <form method="POST"
              action="{{ url_for('admin_delete_customer', customer_id=customer.id) }}"
              onsubmit="return confirm('PERMANENT ACTION: Delete {{ customer.full_name }} and their associated account records? This cannot be undone.');">

            <button type="submit"
                    style="
                    padding:10px 16px;
                    border:0;
                    border-radius:8px;
                    background:#b42318;
                    color:#fff;
                    font-weight:700;
                    cursor:pointer;
                    ">
                Permanently Delete Customer
            </button>

        </form>'''

if old_block in template:

    template = template.replace(
        old_block,
        new_block,
        1
    )

    print("Added Freeze / Unfreeze controls.")
    print("Added Delete Customer control.")

else:

    # If the placeholder has already changed, add controls
    # immediately before the TCC control section.
    if "admin_toggle_customer_freeze" not in template:

        fallback = r'''
        <div style="
            display:flex;
            flex-wrap:wrap;
            gap:10px;
            margin-top:15px;
        ">

            {% if customer.account_status == "Locked" %}

            <form method="POST"
                  action="{{ url_for('admin_toggle_customer_freeze', customer_id=customer.id) }}">

                <button type="submit"
                        style="
                        padding:10px 16px;
                        border:0;
                        border-radius:8px;
                        background:#176b3a;
                        color:#fff;
                        font-weight:700;
                        cursor:pointer;
                        ">
                    Unfreeze Customer Account
                </button>

            </form>

            {% else %}

            <form method="POST"
                  action="{{ url_for('admin_toggle_customer_freeze', customer_id=customer.id) }}"
                  onsubmit="return confirm('Freeze this customer account?');">

                <button type="submit"
                        style="
                        padding:10px 16px;
                        border:0;
                        border-radius:8px;
                        background:#b36b00;
                        color:#fff;
                        font-weight:700;
                        cursor:pointer;
                        ">
                    Freeze Customer Account
                </button>

            </form>

            {% endif %}

            <form method="POST"
                  action="{{ url_for('admin_delete_customer', customer_id=customer.id) }}"
                  onsubmit="return confirm('PERMANENT ACTION: Delete this customer account? This cannot be undone.');">

                <button type="submit"
                        style="
                        padding:10px 16px;
                        border:0;
                        border-radius:8px;
                        background:#b42318;
                        color:#fff;
                        font-weight:700;
                        cursor:pointer;
                        ">
                    Permanently Delete Customer
                </button>

            </form>

        </div>

'''

        marker = '<!-- TCC PAYMENT RESTRICTION CONTROL -->'

        if marker in template:

            template = template.replace(
                marker,
                fallback + marker,
                1
            )

            print("Added Freeze / Unfreeze controls.")
            print("Added Delete Customer control.")

        else:
            print(
                "WARNING: Could not find the customer-control "
                "insertion point."
            )

    else:
        print("Customer freeze/delete controls already exist.")


TEMPLATE.write_text(template, encoding="utf-8")


# =========================================================
# FINAL CHECK
# =========================================================

print()
print("=" * 70)
print(" FINAL CHECK")
print("=" * 70)

updated_app = APP.read_text(encoding="utf-8")
updated_template = TEMPLATE.read_text(encoding="utf-8")

checks = [
    (
        "Freeze route",
        "def admin_toggle_customer_freeze(" in updated_app
    ),
    (
        "Delete route",
        "def admin_delete_customer(" in updated_app
    ),
    (
        "Freeze URL in template",
        "admin_toggle_customer_freeze" in updated_template
    ),
    (
        "Delete URL in template",
        "admin_delete_customer" in updated_template
    ),
    (
        "Existing account_status field",
        "account_status" in updated_app
    ),
]

all_good = True

for name, result in checks:

    if result:
        print("OK:", name)
    else:
        print("MISSING:", name)
        all_good = False


print()

if all_good:
    print("INSTALLATION COMPLETED.")
else:
    print("WARNING: One or more checks failed.")

print()
print("Backups:")
print(" ", app_backup)
print(" ", template_backup)

print()
print("Next step:")
print("  python -m py_compile app.py")

print("=" * 70)