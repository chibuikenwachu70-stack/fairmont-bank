NEWBANKSITE — BREVO SMTP TEST PACKAGE

This package adds a small, separate SMTP helper and a test script. It does not
overwrite app.py, templates, or your database. It does not send customer-facing
transaction/account approval emails; integrate such notifications only after the
application's actual event and authorization logic has been reviewed and tested.

1. Copy email_service.py and test_email.py into your NewBankSite project folder.
2. In your activated Conda environment (newbank), install the dotenv dependency:

   python -m pip install python-dotenv

3. Check the project's .env file contains these keys, with real values locally:

   MAIL_SERVER=smtp-relay.brevo.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=YOUR_BREVO_SMTP_LOGIN
   MAIL_PASSWORD=YOUR_BREVO_SMTP_KEY
   MAIL_DEFAULT_SENDER=support@fairmontbank.com

   Replace the two placeholders on your own computer. Never share the SMTP key.

4. Ensure .env is listed in .gitignore. Do not commit it to GitHub or upload it.
5. Run this from the project folder:

   python test_email.py

6. Enter an inbox you control, such as fairmontbank@gmail.com. Check Inbox and Spam.

If the test fails, share the error text only after removing any credentials or tokens.
Do not send SMTP keys or passwords in chat.

SENDER REQUIREMENT
Brevo shows support@fairmontbank.com as verified and domain DKIM/DMARC as configured
in your screenshot. Use that address only while you control/are authorized to send from it.

IMPORTANT
An SMTP success means Brevo accepted the message; it does not prove final delivery.
Only send account/payment/transaction emails when the corresponding authorized event
really occurred and the application records it accurately. Do not use these emails as
proof of real banking activity for a simulated application.
