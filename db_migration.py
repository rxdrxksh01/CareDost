from db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE patients ADD COLUMN initiation_credits INTEGER DEFAULT 0'))
        conn.commit()
    except Exception as e:
        print(f"initiation_credits: {e}")
        
    try:
        conn.execute(text('ALTER TABLE patients ADD COLUMN reply_credits INTEGER DEFAULT 0'))
        conn.commit()
    except Exception as e:
        print(f"reply_credits: {e}")
    
    print("Done")
