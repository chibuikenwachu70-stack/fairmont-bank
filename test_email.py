"""Send one clearly labeled test email to an inbox you control."""
import getpass
import sys
from email_service import send_email

recipient = input("Your own test inbox (e.g. fairmontbank@gmail.com): ").strip()
try:
    send_email(
        recipient,
        "NewBankSite — SMTP delivery test",
        "This is a test message to verify the configured Brevo SMTP connection.\n\n"
        "It is not a transaction receipt, account approval, or proof of a financial event.\n"
        "If you did not request this test, you can ignore this message.",
    )
except Exception as exc:
    print(f"EMAIL TEST FAILED: {type(exc).__name__}: {exc}")
    sys.exit(1)
else:
    print("SMTP accepted the test message. Check your inbox and spam folder.")
    print("This confirms SMTP submission, not guaranteed inbox delivery.")
