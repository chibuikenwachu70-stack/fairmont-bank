import os
import re
import ast
from datetime import datetime

APP_FILE = "app.py"
TEMPLATE_DIR = "templates"

print("=" * 60)
print(" SEND MONEY INVESTIGATION")
print("=" * 60)
print()

if not os.path.exists(APP_FILE):
    print("ERROR: app.py was not found.")
    input("Press Enter to close...")
    raise SystemExit

with open(APP_FILE, "r", encoding="utf-8") as f:
    app_code = f.read()

template_file = os.path.join(TEMPLATE_DIR, "send_money.html")

if not os.path.exists(template_file):
    print("ERROR: templates/send_money.html was not found.")
    input("Press Enter to close...")
    raise SystemExit

with open(template_file, "r", encoding="utf-8") as f:
    template_code = f.read()

# ---------------------------------------------------------
# 1. FIND ALL FLASK ROUTES
# ---------------------------------------------------------

print("--- 1. FLASK ROUTES IN app.py ---")

route_pattern = re.compile(
    r"@app\.route\((.*?)\)\s*\n\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.DOTALL
)

routes = route_pattern.findall(app_code)

if routes:
    for route_text, function_name in routes:
        clean_route = " ".join(route_text.split())
        print(f"FUNCTION: {function_name}")
        print(f"ROUTE:    {clean_route}")
        print()
else:
    print("NO ROUTES FOUND.")

# ---------------------------------------------------------
# 2. CHECK FOR send_money
# ---------------------------------------------------------

print("--- 2. send_money ENDPOINT ---")

send_money_match = re.search(
    r"def\s+send_money\s*\(",
    app_code
)

if send_money_match:
    print("FOUND: def send_money()")
    print(f"Position in app.py: {send_money_match.start()}")
else:
    print("NOT FOUND: def send_money()")

print()

# ---------------------------------------------------------
# 3. CHECK FOR send_fairmont_money
# ---------------------------------------------------------

print("--- 3. send_fairmont_money ENDPOINT ---")

fairmont_function = re.search(
    r"def\s+send_fairmont_money\s*\(",
    app_code
)

if fairmont_function:
    print("FOUND: def send_fairmont_money()")
    print(f"Position in app.py: {fairmont_function.start()}")
else:
    print("NOT FOUND: def send_fairmont_money()")

print()

# ---------------------------------------------------------
# 4. FIND ALL REFERENCES IN app.py
# ---------------------------------------------------------

print("--- 4. send_fairmont_money REFERENCES IN app.py ---")

app_references = []

for number, line in enumerate(app_code.splitlines(), start=1):
    if "send_fairmont_money" in line:
        app_references.append((number, line))

if app_references:
    for number, line in app_references:
        print(f"{number}: {line}")
else:
    print("NO REFERENCES FOUND IN app.py.")

print()

# ---------------------------------------------------------
# 5. FIND ALL REFERENCES IN send_money.html
# ---------------------------------------------------------

print("--- 5. ENDPOINT REFERENCES IN send_money.html ---")

url_refs = re.findall(
    r"url_for\(\s*['\"]([^'\"]+)['\"]",
    template_code
)

if url_refs:
    seen = set()

    for endpoint in url_refs:
        if endpoint not in seen:
            seen.add(endpoint)
            print(f"url_for endpoint: {endpoint}")
else:
    print("NO url_for() REFERENCES FOUND.")

print()

# ---------------------------------------------------------
# 6. CHECK WHICH TEMPLATE ENDPOINTS EXIST
# ---------------------------------------------------------

print("--- 6. TEMPLATE ENDPOINT CHECK ---")

function_names = {
    name for _, name in routes
}

unique_endpoints = []
for endpoint in url_refs:
    if endpoint not in unique_endpoints:
        unique_endpoints.append(endpoint)

if unique_endpoints:
    for endpoint in unique_endpoints:
        if endpoint in function_names:
            print(f"[OK]      {endpoint}")
        else:
            print(f"[MISSING] {endpoint}")
else:
    print("No endpoints to check.")

print()

# ---------------------------------------------------------
# 7. SHOW send_money FUNCTION
# ---------------------------------------------------------

print("--- 7. send_money FUNCTION SOURCE ---")

lines = app_code.splitlines()

send_start = None

for i, line in enumerate(lines):
    if re.match(r"\s*def\s+send_money\s*\(", line):
        send_start = i
        break

if send_start is not None:
    end = len(lines)

    for i in range(send_start + 1, len(lines)):
        if re.match(r"^\s*@app\.route", lines[i]):
            end = i
            break

    for number in range(send_start, min(end, send_start + 180)):
        print(f"{number + 1}: {lines[number]}")
else:
    print("send_money() function could not be located.")

print()

# ---------------------------------------------------------
# 8. SHOW LINES AROUND THE BROKEN TEMPLATE REFERENCE
# ---------------------------------------------------------

print("--- 8. send_money.html AROUND BROKEN REFERENCE ---")

template_lines = template_code.splitlines()

found_template_reference = False

for i, line in enumerate(template_lines):
    if "send_fairmont_money" in line:
        found_template_reference = True

        start = max(0, i - 12)
        end = min(len(template_lines), i + 13)

        for number in range(start, end):
            print(f"{number + 1}: {template_lines[number]}")

        print()

if not found_template_reference:
    print("send_fairmont_money was not found in send_money.html.")

# ---------------------------------------------------------
# 9. CHECK FOR OTHER POSSIBLE BROKEN url_for REFERENCES
# ---------------------------------------------------------

print("--- 9. ALL url_for() REFERENCES WITH STATUS ---")

for endpoint in unique_endpoints:
    status = "EXISTS" if endpoint in function_names else "MISSING"
    print(f"{status}: {endpoint}")

print()
print("=" * 60)
print(" INVESTIGATION COMPLETE")
print("=" * 60)
print()
print("No files were modified.")
print("No database records were changed.")
print("No customer accounts were changed.")
print("No transactions were changed.")
print()
print("This investigation only reads app.py and send_money.html.")
print()

input("Press Enter to close...")