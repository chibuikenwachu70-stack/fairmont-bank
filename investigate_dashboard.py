from pathlib import Path

APP = Path("app.py")
TEMPLATE = Path("templates/dashboard.html")

print("=" * 60)
print(" DASHBOARD INVESTIGATION")
print("=" * 60)

app_lines = APP.read_text(encoding="utf-8").splitlines()
template_lines = TEMPLATE.read_text(encoding="utf-8").splitlines()

print("\n--- DASHBOARD FUNCTION IN app.py ---")

start = None

for i, line in enumerate(app_lines):
    if line.strip().startswith("def dashboard("):
        start = i
        break

if start is None:
    print("ERROR: dashboard() was not found.")
else:
    end = len(app_lines)

    for i in range(start + 1, len(app_lines)):
        if (
            app_lines[i].startswith("@app.route(")
            or app_lines[i].strip().startswith("def ")
        ):
            end = i
            break

    for i in range(start, end):
        print(f"{i + 1}: {app_lines[i]}")

print("\n--- BALANCE VARIABLES IN dashboard.html ---")

for i, line in enumerate(template_lines):
    if any(
        word in line
        for word in [
            "display_balance",
            "account_balance",
            "currency_symbol",
            "balance",
        ]
    ):
        print(f"{i + 1}: {line}")

print("\n--- RENDER_TEMPLATE VARIABLES ---")

if start is not None:
    for i in range(start, end):
        if "render_template(" in app_lines[i]:
            print(f"\nStarting at line {i + 1}:")
            for j in range(i, min(i + 80, end)):
                print(f"{j + 1}: {app_lines[j]}")

print("\n" + "=" * 60)
print(" INVESTIGATION COMPLETE")
print("=" * 60)
print("\nNo files were modified.")
print("No database records were changed.")
print("No customer accounts were changed.")
print("\nPress Enter to close...")
input()