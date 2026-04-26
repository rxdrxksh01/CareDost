from sqlalchemy import create_engine, text
from db.database import Base
import db.models  # noqa: F401
import os


def main():
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise ValueError("DATABASE_URL must be PostgreSQL for this script.")

    engine = create_engine(db_url)
    metadata = Base.metadata

    with engine.begin() as conn:
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
            print(f"{table_name}: sequence fixed")

    print("Done.")


if __name__ == "__main__":
    main()
