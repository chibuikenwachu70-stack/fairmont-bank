import re
from pathlib import Path

APP = Path("app.py")
TEMPLATE = Path("templates/dashboard.html")

print("=" * 60)
print(" DASHBOARD INVESTIGATION 2")
print("=" * 60)

app_text = APP.read_text(encoding="utf-8")
template_text = TEMPLATE.read_text(encoding="utf-8")

print("\n--- 1. CURRENCY VARIABLES IN dashboard.html ---")

for i, line in enumerate(template_text.splitlines(), 1):
    if "currency_" in line:
        print(f"{i}: {line}")

print("\n--- 2. CURRENCY VARIABLES IN app.py ---")

for i, line in enumerate(app_text.splitlines(), 1):
    if "CURRENCY_" in line or "currency_locale" in line or "currency_symbol" in line:
        print(f"{i}: {line}")

print("\n--- 3. DASHBOARD render_template() ---")

lines = app_text.splitlines()

dashboard_start = None

for i, line in enumerate(lines):
    if line.strip() == "def dashboard():":
        dashboard_start = i
        break

if dashboard_start is None:
    print("ERROR: dashboard() was not found.")
else:
    dashboard_end = len(lines)

    for i in range(dashboard_start + 1, len(lines)):
        if lines[i].startswith("def ") and i > dashboard_start:
            dashboard_end = i
            break

    dashboard_block = lines[dashboard_start:dashboard_end]

    for i, line in enumerate(dashboard_block, dashboard_start + 1):
        print(f"{i}: {line}")

    print("\n--- 4. VALUES PASSED TO dashboard.html ---")

    render_start = None

    for i, line in enumerate(dashboard_block):
        if "return render_template(" in line and '"dashboard.html"' in "\n".join(dashboard_block[i:i+5]):
            render_start = i
            break

    if render_start is None:
        print("Could not locate dashboard.html render_template().")
    else:
        for line in dashboard_block[render_start:render_start + 30]:
            print(line)

print("\n--- 5. currency_locale USAGE ---")

matches = list(re.finditer(r"currency_locale", app_text))

if not matches:
    print("currency_locale does NOT appear anywhere in app.py.")
else:
    print(f"currency_locale appears {len(matches)} time(s) in app.py.")

print("\n--- 6. currency_locale DEFINITION CHECK ---")

definition_patterns = [
    r"currency_locale\s*=",
    r"['\"]currency_locale['\"]\s*:",
    r"currency_locale\s*:",
]

found_definition = False

for pattern in definition_patterns:
    if re.search(pattern, app_text):
        found_definition = True
        print("Possible definition found:", pattern)

if not found_definition:
    print("NO currency_locale definition found in app.py.")

print("\n--- 7. CONFIGURATION ---")

for i, line in enumerate(lines, 1):
    if "CURRENCY" in line.upper():
        print(f"{i}: {line}")

print("\n" + "=" * 60)
print(" INVESTIGATION COMPLETE")
print("=" * 60)

print("\nNo files were modified.")
print("No database records were changed.")
print("No customer accounts were changed.")
print("\nPress Enter to close...")
input()