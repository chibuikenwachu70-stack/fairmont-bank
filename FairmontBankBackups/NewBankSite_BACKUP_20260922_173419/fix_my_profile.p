from pathlib import Path


BASE_DIR = Path(r"C:\Users\DON J\Documents\NewBankSite")

APP_FILE = BASE_DIR / "app.py"
PROFILE_TEMPLATE = BASE_DIR / "templates" / "my_profile.html"
CSS_FILE = BASE_DIR / "static" / "css" / "style.css"


# =========================================================
# ADD MY PROFILE ROUTE TO APP.PY
# =========================================================

app_text = APP_FILE.read_text(encoding="utf-8")


profile_route = '''

# =========================================================
# MY PROFILE
# =========================================================

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

'''


if '@app.route("/my-profile")' not in app_text:

    logout_marker = '@app.route("/logout")'

    if logout_marker not in app_text:

        print("ERROR: Could not find the logout route in app.py.")
        raise SystemExit(1)

    app_text = app_text.replace(
        logout_marker,
        profile_route + logout_marker,
        1
    )

    APP_FILE.write_text(
        app_text,
        encoding="utf-8"
    )

    print("SUCCESS: My Profile route added to app.py.")

else:

    print("My Profile route already exists.")


# =========================================================
# CREATE MY PROFILE TEMPLATE
# =========================================================

PROFILE_TEMPLATE.parent.mkdir(
    parents=True,
    exist_ok=True
)


profile_html = '''<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0">

    <title>My Profile | Fairmont Bank</title>

    <link
        rel="stylesheet"
        href="{{ url_for('static', filename='css/style.css') }}">

</head>

<body>

    <main class="profile-page">

        <div class="profile-shell">


            <header class="profile-page-header">

                <a
                    href="/login"
                    class="profile-back-button">

                    ←

                </a>

                <div class="profile-page-title">

                    <p>
                        FAIRMONT BANK
                    </p>

                    <h1>
                        My Profile
                    </h1>

                </div>

            </header>


            <section class="profile-identity-card">

                <div class="large-profile-avatar">

                    {{ customer.full_name[0].upper() }}

                </div>


                <div class="profile-identity-details">

                    <h2>
                        {{ customer.full_name }}
                    </h2>

                    <p>
                        Customer ID · {{ customer.customer_id }}
                    </p>

                    <span class="profile-status">

                        <span class="status-dot"></span>

                        {{ customer.account_status }}

                    </span>

                </div>

            </section>


            <section class="profile-section">

                <div class="profile-section-heading">

                    <p>
                        PERSONAL INFORMATION
                    </p>

                    <h2>
                        Personal details
                    </h2>

                </div>


                <div class="profile-details-card">


                    <div class="profile-detail-row">

                        <div class="profile-detail-label">
                            Full name
                        </div>

                        <div class="profile-detail-value">
                            {{ customer.full_name }}
                        </div>

                    </div>


                    <div class="profile-detail-row">

                        <div class="profile-detail-label">
                            Email address
                        </div>

                        <div class="profile-detail-value">
                            {{ customer.email }}
                        </div>

                    </div>


                    <div class="profile-detail-row">

                        <div class="profile-detail-label">
                            Phone number
                        </div>

                        <div class="profile-detail-value">
                            {{ customer.phone }}
                        </div>

                    </div>


                    <div class="profile-detail-row">

                        <div class="profile-detail-label">
                            Country of residence
                        </div>

                        <div class="profile-detail-value">
                            {{ customer.country }}
                        </div>

                    </div>


                </div>

            </section>


            <section class="profile-section">

                <div class="profile-section-heading">

                    <p>
                        ACCOUNT INFORMATION
                    </p>

                    <h2>
                        Account details
                    </h2>

                </div>


                <div class="profile-details-card">


                    <div class="profile-detail-row">

                        <div class="profile-detail-label">
                            Customer ID
                        </div>

                        <div class="profile-detail-value">
                            {{ customer.customer_id }}
                        </div>

                    </div>


                    <div class="profile-detail-row">

                        <div class="profile-detail-label">
                            Account type
                        </div>

                        <div class="profile-detail-value account-type-value">
                            {{ customer.account_type }}
                        </div>

                    </div>


                    <div class="profile-detail-row">

                        <div class="profile-detail-label">
                            Account status
                        </div>

                        <div class="profile-detail-value profile-active-status">
                            {{ customer.account_status }}
                        </div>

                    </div>


                    <div class="profile-detail-row">

                        <div class="profile-detail-label">
                            Available balance
                        </div>

                        <div class="profile-detail-value profile-balance-value">

                            £{{ "{:,.2f}".format(customer.account_balance) }}

                        </div>

                    </div>


                </div>

            </section>


            <section class="profile-section">

                <div class="profile-section-heading">

                    <p>
                        SECURITY
                    </p>

                    <h2>
                        Account security
                    </h2>

                </div>


                <div class="profile-security-card">

                    <div class="security-check">
                        ✓
                    </div>

                    <div>

                        <strong>
                            Your account is protected
                        </strong>

                        <p>
                            Your password is securely stored and your account information is protected.
                        </p>

                    </div>

                </div>

            </section>


            <a
                href="/login"
                class="profile-dashboard-button">

                Return to dashboard

            </a>


            <a
                href="/logout"
                class="profile-logout">

                Sign out

            </a>


        </div>

    </main>

</body>

</html>
'''


PROFILE_TEMPLATE.write_text(
    profile_html,
    encoding="utf-8"
)

print("SUCCESS: my_profile.html created.")


# =========================================================
# ADD PROFILE CSS
# =========================================================

profile_css = '''

/* =========================================================
   FAIRMONT BANK - MY PROFILE
   ========================================================= */

.profile-page {
    min-height: 100vh;
    min-height: 100svh;

    background:
        radial-gradient(
            circle at 90% 0%,
            rgba(72, 143, 173, 0.16),
            transparent 35%
        ),
        linear-gradient(
            145deg,
            #071d30 0%,
            #092a3f 50%,
            #061523 100%
        );

    color: #ffffff;
}


.profile-shell {
    width: 100%;
    max-width: 620px;

    margin: 0 auto;

    padding: 24px 20px 50px;
}


.profile-page-header {
    display: flex;

    align-items: center;

    gap: 15px;

    margin-bottom: 25px;
}


.profile-back-button {
    width: 42px;
    height: 42px;

    flex: 0 0 42px;

    display: flex;

    align-items: center;
    justify-content: center;

    border-radius: 13px;

    background:
        rgba(255, 255, 255, 0.07);

    border: 1px solid rgba(255, 255, 255, 0.10);

    color: #ffffff;

    font-size: 20px;

    text-decoration: none;
}


.profile-page-title p {
    margin-bottom: 4px;

    font-size: 9px;

    font-weight: 700;

    letter-spacing: 1.8px;

    color: rgba(255, 255, 255, 0.42);
}


.profile-page-title h1 {
    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 25px;

    font-weight: 500;

    letter-spacing: -0.4px;
}


.profile-identity-card {
    display: flex;

    align-items: center;

    gap: 17px;

    padding: 21px;

    border-radius: 21px;

    background:
        linear-gradient(
            135deg,
            rgba(255, 255, 255, 0.13),
            rgba(255, 255, 255, 0.055)
        );

    border: 1px solid rgba(255, 255, 255, 0.12);

    box-shadow:
        0 18px 45px rgba(0, 0, 0, 0.18);
}


.large-profile-avatar {
    width: 66px;
    height: 66px;

    flex: 0 0 66px;

    display: flex;

    align-items: center;
    justify-content: center;

    border-radius: 50%;

    background:
        linear-gradient(
            145deg,
            rgba(255, 255, 255, 0.18),
            rgba(255, 255, 255, 0.07)
        );

    border: 1px solid rgba(255, 255, 255, 0.15);

    font-size: 24px;

    font-weight: 600;
}


.profile-identity-details h2 {
    font-size: 18px;

    font-weight: 600;

    color: #ffffff;
}


.profile-identity-details p {
    margin-top: 5px;

    font-size: 10px;

    color: rgba(255, 255, 255, 0.43);
}


.profile-status {
    display: inline-flex;

    align-items: center;

    gap: 6px;

    margin-top: 9px;

    padding: 5px 9px;

    border-radius: 8px;

    background:
        rgba(183, 228, 199, 0.08);

    color: #b7e4c7;

    font-size: 9px;

    font-weight: 600;
}


.status-dot {
    width: 6px;
    height: 6px;

    border-radius: 50%;

    background: #b7e4c7;
}


.profile-section {
    margin-top: 28px;
}


.profile-section-heading {
    margin-bottom: 12px;
}


.profile-section-heading p {
    margin-bottom: 4px;

    font-size: 9px;

    font-weight: 700;

    letter-spacing: 1.5px;

    color: rgba(255, 255, 255, 0.40);
}


.profile-section-heading h2 {
    font-size: 16px;

    font-weight: 600;

    color: #ffffff;
}


.profile-details-card {
    padding: 4px 17px;

    border-radius: 18px;

    background:
        rgba(255, 255, 255, 0.055);

    border: 1px solid rgba(255, 255, 255, 0.09);
}


.profile-detail-row {
    min-height: 61px;

    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 20px;

    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}


.profile-detail-row:last-child {
    border-bottom: 0;
}


.profile-detail-label {
    flex: 0 0 auto;

    font-size: 11px;

    color: rgba(255, 255, 255, 0.45);
}


.profile-detail-value {
    max-width: 60%;

    font-size: 12px;

    font-weight: 600;

    line-height: 1.35;

    text-align: right;

    color: rgba(255, 255, 255, 0.90);

    overflow-wrap: anywhere;
}


.account-type-value {
    text-transform: capitalize;
}


.profile-active-status {
    color: #b7e4c7;
}


.profile-balance-value {
    font-size: 14px;

    color: #ffffff;
}


.profile-security-card {
    display: flex;

    align-items: flex-start;

    gap: 13px;

    padding: 17px;

    border-radius: 18px;

    background:
        rgba(255, 255, 255, 0.045);

    border: 1px solid rgba(255, 255, 255, 0.08);
}


.security-check {
    width: 31px;
    height: 31px;

    flex: 0 0 31px;

    display: flex;

    align-items: center;
    justify-content: center;

    border-radius: 10px;

    background:
        rgba(183, 228, 199, 0.10);

    color: #b7e4c7;

    font-size: 13px;

    font-weight: 700;
}


.profile-security-card strong {
    display: block;

    margin-bottom: 5px;

    font-size: 12px;

    color: rgba(255, 255, 255, 0.88);
}


.profile-security-card p {
    font-size: 10px;

    line-height: 1.5;

    color: rgba(255, 255, 255, 0.42);
}


.profile-dashboard-button {
    display: flex;

    align-items: center;
    justify-content: center;

    width: 100%;

    min-height: 50px;

    margin-top: 30px;

    border-radius: 14px;

    background:
        linear-gradient(
            135deg,
            rgba(255, 255, 255, 0.15),
            rgba(255, 255, 255, 0.07)
        );

    border: 1px solid rgba(255, 255, 255, 0.12);

    color: #ffffff;

    font-size: 12px;

    font-weight: 600;

    text-decoration: none;
}


.profile-logout {
    display: block;

    width: fit-content;

    margin: 18px auto 0;

    padding: 8px 12px;

    border-radius: 9px;

    color: rgba(255, 255, 255, 0.45);

    font-size: 11px;

    text-decoration: none;

    background:
        rgba(255, 255, 255, 0.035);
}


@media (max-width: 430px) {

    .profile-shell {
        padding-left: 16px;
        padding-right: 16px;
    }

    .profile-identity-card {
        padding: 17px;
    }

    .large-profile-avatar {
        width: 58px;
        height: 58px;

        flex-basis: 58px;
    }

}
'''


css_text = CSS_FILE.read_text(encoding="utf-8")


if ".profile-page {" not in css_text:

    CSS_FILE.write_text(
        css_text + profile_css,
        encoding="utf-8"
    )

    print("SUCCESS: My Profile CSS added.")

else:

    print("My Profile CSS already exists.")


print()
print("==============================================")
print("MY PROFILE FIX COMPLETED")
print("==============================================")
print()
print("The following were added:")
print("1. /my-profile route")
print("2. templates/my_profile.html")
print("3. My Profile CSS")
print()