import app
import inspect

print("=" * 70)
print(" FAIRMONT BANK - PROFILE ROUTE SEARCH")
print("=" * 70)
print()

print("Functions containing profile:")
print()

for name in dir(app):
    if "profile" in name.lower():
        obj = getattr(app, name)

        if callable(obj):
            print("-" * 60)
            print("FUNCTION:", name)

            try:
                print(inspect.getsource(obj))
            except Exception as e:
                print("Could not read source:", e)

print()
print("=" * 70)
print(" ALL CUSTOMER ROUTES")
print("=" * 70)
print()

for rule in app.app.url_map.iter_rules():
    endpoint = rule.endpoint.lower()

    if (
        "customer" in endpoint
        or "profile" in endpoint
        or "account" in endpoint
    ):
        print(f"{rule} -> {rule.endpoint}")

print()
print("=" * 70)
print(" SEARCH COMPLETE")
print("=" * 70)