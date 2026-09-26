from pathlib import Path

print("=" * 70)
print(" FAIRMONT BANK - EXACT /MY-PROFILE REGISTRATION SEARCH")
print("=" * 70)
print()

p = Path("app.py")

if not p.exists():
    print("[ERROR] app.py not found.")
    raise SystemExit(1)

lines = p.read_text(encoding="utf-8").splitlines()

found = False

for i, line in enumerate(lines):

    if "/my-profile" in line:

        found = True

        print("-" * 70)
        print(f"FOUND /my-profile AT LINE {i + 1}")
        print("-" * 70)

        start = max(0, i - 8)
        end = min(len(lines), i + 12)

        for n in range(start, end):
            print(f"{n + 1}: {lines[n]}")

        print()

if not found:
    print("[ERROR] The text /my-profile was not found anywhere in app.py.")

print("=" * 70)
print(" SEARCH COMPLETE")
print("=" * 70)