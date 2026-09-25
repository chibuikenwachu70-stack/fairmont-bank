import os
import sqlite3
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.exc import SQLAlchemyError

SOURCE_DB = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "instance", "fairmont.db")

)

TARGET_URL = os.environ.get("TARGET_DATABASE_URL")

if not TARGET_URL:
    raise RuntimeError(
        "TARGET_DATABASE_URL is not set. Set it to your Render External Database URL."
    )

if not os.path.exists(SOURCE_DB):
    raise FileNotFoundError(f"SQLite database not found: {SOURCE_DB}")

print("=" * 60)
print("FAIRMONT BANK - SQLITE TO POSTGRESQL MIGRATION")
print("=" * 60)
print(f"Source: {SOURCE_DB}")
print("Target: Render PostgreSQL")
print()

# Import the Flask application's SQLAlchemy models.
# DATABASE_URL is deliberately NOT used here because we only
# need the model metadata from app.py.
os.environ["DATABASE_URL"] = "sqlite:///" + SOURCE_DB

from app import db

sqlite_engine = create_engine("sqlite:///" + SOURCE_DB)
postgres_engine = create_engine(TARGET_URL)

# Use the application's SQLAlchemy metadata as the authoritative schema.
metadata = db.metadata

print("Creating PostgreSQL tables...")
metadata.create_all(postgres_engine)
print("PostgreSQL schema ready.")
print()

# Get table names from SQLite.
with sqlite_engine.connect() as source_conn:
    source_tables = [
        row[0]
        for row in source_conn.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
        )
    ]

print("SQLite tables found:")
for name in source_tables:
    print(f"  - {name}")

print()

# Only migrate tables that exist in both SQLite and the application's metadata.
tables_to_migrate = [
    name for name in source_tables
    if name in metadata.tables
]

print("Tables selected for migration:")
for name in tables_to_migrate:
    print(f"  - {name}")

print()

# Determine a dependency-safe order from SQLAlchemy foreign keys.
table_objects = {
    name: metadata.tables[name]
    for name in tables_to_migrate
}

dependencies = {
    name: {
        fk.column.table.name
        for fk in table.foreign_keys
        if fk.column.table.name in tables_to_migrate
        and fk.column.table.name != name
    }
    for name, table in table_objects.items()
}

ordered = []
remaining = set(tables_to_migrate)

while remaining:
    ready = sorted(
        name for name in remaining
        if dependencies[name].issubset(set(ordered))
    )

    if not ready:
        # If there is a circular dependency, continue with a stable order.
        ready = [sorted(remaining)[0]]

    ordered.extend(ready)
    remaining.difference_update(ready)

print("Migration order:")
for name in ordered:
    print(f"  - {name}")

print()

total_rows = 0

try:
    with sqlite_engine.connect() as source_conn:
        with postgres_engine.begin() as target_conn:

            for table_name in ordered:
                table = table_objects[table_name]

                columns = [column.name for column in table.columns]

                result = source_conn.execute(
                    table.select()
                )

                rows = result.mappings().all()

                if not rows:
                    print(f"{table_name}: 0 rows")
                    continue

                # Insert in batches.
                batch_size = 500

                inserted = 0

                for start in range(0, len(rows), batch_size):
                    batch = rows[start:start + batch_size]

                    values = [
                        {
                            column: row[column]
                            for column in columns
                        }
                        for row in batch
                    ]

                    target_conn.execute(
                        table.insert(),
                        values
                    )

                    inserted += len(values)

                total_rows += inserted
                print(f"{table_name}: {inserted} rows")

            # Reset PostgreSQL sequences for integer primary keys.
            print()
            print("Updating PostgreSQL sequences...")

            for table_name in ordered:
                table = table_objects[table_name]

                for column in table.primary_key.columns:
                    if column.name.lower() != "id":
                        continue

                    try:
                        result = target_conn.execute(
                            text(
                                f'SELECT MAX("{column.name}") '
                                f'FROM "{table_name}"'
                            )
                        )

                        max_id = result.scalar()

                        if max_id is not None:
                            sequence_result = target_conn.execute(
                                text(
                                    "SELECT pg_get_serial_sequence(:table_name, :column_name)"
                                ),
                                {
                                    "table_name": table_name,
                                    "column_name": column.name,
                                },
                            )

                            sequence_name = sequence_result.scalar()

                            if sequence_name:
                                target_conn.execute(
                                    text(
                                        "SELECT setval("
                                        ":sequence_name::regclass, "
                                        ":max_id, true)"
                                    ),
                                    {
                                        "sequence_name": sequence_name,
                                        "max_id": int(max_id),
                                    },
                                )

                    except Exception as exc:
                        print(
                            f"  Sequence warning for {table_name}: {exc}"
                        )

    print()
    print("=" * 60)
    print("MIGRATION COMPLETED")
    print(f"Total rows migrated: {total_rows}")
    print("=" * 60)

except SQLAlchemyError as exc:
    print()
    print("=" * 60)
    print("MIGRATION FAILED")
    print("=" * 60)
    print(str(exc))
    raise