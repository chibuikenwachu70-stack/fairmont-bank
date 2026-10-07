from app import app, db, Bank

with app.app_context():
    print("\n=== ALL ACTIVE BANKS ===")

    banks = Bank.query.filter_by(active=True).order_by(Bank.name.asc()).all()

    if not banks:
        print("NO ACTIVE BANKS FOUND.")
    else:
        for bank in banks:
            print(
                f"ID={bank.id} | "
                f"NAME={bank.name!r} | "
                f"COUNTRY={bank.country!r} | "
                f"ACTIVE={bank.active!r}"
            )

    print("\n=== FAIRMONT SEARCH ===")

    fairmont = Bank.query.filter(
        Bank.name.ilike("%Fairmont%")
    ).all()

    if not fairmont:
        print("Fairmont Bank does NOT exist in the database.")
    else:
        for bank in fairmont:
            print(
                f"FOUND: ID={bank.id} | "
                f"NAME={bank.name!r} | "
                f"COUNTRY={bank.country!r} | "
                f"ACTIVE={bank.active!r}"
            )

    print("\n=== COUNTRY VALUES ===")

    countries = db.session.query(Bank.country).distinct().order_by(Bank.country).all()

    for country in countries:
        print(repr(country[0]))