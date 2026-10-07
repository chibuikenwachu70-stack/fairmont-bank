from pathlib import Path
import sqlite3
import secrets
import string

DB_FILE = Path(
    r"C:\Users\DON J\Documents\NewBankSite\instance\fairmont.db"
)

TARGET_CUSTOMER_ID = "FB69443295"


def generate_account_number(connection):
    while True:
        account_number = "".join(
            secrets.choice(string.digits)
            for _ in range(10)
        )

        row = connection.execute(
            """
            SELECT customer_id
            FROM customer
            WHERE account_number = ?
            """,
            (account_number,)
        ).fetchone()

        if row is None:
            return account_number


connection = sqlite3.connect(DB_FILE)

try:
    connection.execute("PRAGMA foreign_keys = ON")

    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(customer)"
        ).fetchall()
    }

    if "account_number" not in columns:
        connection.execute(
            """
            ALTER TABLE customer
            ADD COLUMN account_number VARCHAR(12)
            """
        )

        print("SUCCESS: Account Number column added to database.")

    customer = connection.execute(
        """
        SELECT customer_id, full_name, account_number, account_balance
        FROM customer
        WHERE customer_id = ?
        """,
        (TARGET_CUSTOMER_ID,)
    ).fetchone()

    if customer is None:
        print(
            f"ERROR: Customer {TARGET_CUSTOMER_ID} was not found."
        )

    elif customer[2]:
        print(
            f"Account Number already exists for {TARGET_CUSTOMER_ID}: "
            f"{customer[2]}"
        )

    else:
        account_number = generate_account_number(connection)

        connection.execute(
            """
            UPDATE customer
            SET account_number = ?
            WHERE customer_id = ?
            """,
            (
                account_number,
                TARGET_CUSTOMER_ID
            )
        )

        connection.commit()

        print("")
        print("==============================================")
        print("EXISTING CUSTOMER UPDATED")
        print("==============================================")
        print(f"Customer ID:     {TARGET_CUSTOMER_ID}")
        print(f"Account Number:  {account_number}")
        print(f"Existing Name:   {customer[1]}")
        print(f"Existing Balance: £{float(customer[3] or 0):,.2f}")
        print("")
        print("Password was not changed.")
        print("Balance was not changed.")
        print("Other customer information was not changed.")
        print("")

finally:
    connection.close()