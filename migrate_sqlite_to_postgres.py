import argparse
import os
from sqlalchemy import MetaData, create_engine, select, text
from db.database import Base
import db.models  # noqa: F401  # ensure models are registered on Base


def parse_args():
    parser = argparse.ArgumentParser(
        description="Copy data from local SQLite (clinic.db) to Postgres (Neon)."
    )
    parser.add_argument(
        "--source",
        default="sqlite:///clinic.db",
        help="Source database URL (default: sqlite:///clinic.db)",
    )
    parser.add_argument(
        "--target",
        default=os.getenv("NEW_DATABASE_URL") or os.getenv("DATABASE_URL"),
        help="Target Postgres URL (or set NEW_DATABASE_URL / DATABASE_URL)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow insert even if target tables already have rows",
    )
    return parser.parse_args()


def validate_target(url: str):
    if not url:
        raise ValueError("Missing target DB URL. Pass --target or set NEW_DATABASE_URL.")
    if not url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise ValueError("Target must be a Postgres URL.")


def reset_postgres_sequences(conn, metadata):
    """Align SERIAL sequences with imported row IDs."""
    for table_name, table in metadata.tables.items():
        if "id" not in table.columns:
            continue
        conn.execute(
            text(
                f"""
                SELECT setval(
                  pg_get_serial_sequence('{table_name}', 'id'),
                  COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1,
                  false
                )
                """
            )
        )
        print(f"{table_name}: sequence reset")


def main():
    args = parse_args()
    validate_target(args.target)

    source_engine = create_engine(args.source)
    target_engine = create_engine(args.target)

    # Create target schema using current SQLAlchemy models.
    Base.metadata.create_all(bind=target_engine)

    source_meta = MetaData()
    source_meta.reflect(bind=source_engine)

    target_meta = MetaData()
    target_meta.reflect(bind=target_engine)

    with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
        for source_table in source_meta.sorted_tables:
            table_name = source_table.name
            if table_name not in target_meta.tables:
                print(f"Skipping {table_name}: not present in target metadata")
                continue

            target_table = target_meta.tables[table_name]
            target_count = target_conn.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar_one()
            if target_count > 0 and not args.force:
                print(
                    f"Skipping {table_name}: target already has {target_count} rows "
                    "(use --force to override)"
                )
                continue

            rows = source_conn.execute(select(source_table)).mappings().all()
            if not rows:
                print(f"{table_name}: 0 rows")
                continue

            payload = [dict(row) for row in rows]
            target_conn.execute(target_table.insert(), payload)
            print(f"{table_name}: copied {len(payload)} rows")

        reset_postgres_sequences(target_conn, target_meta)

    print("Migration completed.")


if __name__ == "__main__":
    main()
