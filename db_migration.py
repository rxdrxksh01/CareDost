from db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Patient credits (already there but safe to retry)
    try:
        conn.execute(text('ALTER TABLE patients ADD COLUMN initiation_credits INTEGER DEFAULT 0'))
        conn.commit()
    except Exception: pass
        
    try:
        conn.execute(text('ALTER TABLE patients ADD COLUMN reply_credits INTEGER DEFAULT 0'))
        conn.commit()
    except Exception: pass

    # Patient Message attachments [NEW]
    try:
        conn.execute(text('ALTER TABLE patient_messages ADD COLUMN file_path TEXT'))
        conn.commit()
        print("Added file_path to patient_messages")
    except Exception as e:
        print(f"file_path: {e}")

    try:
        conn.execute(text('ALTER TABLE patient_messages ADD COLUMN is_image BOOLEAN DEFAULT 0'))
        conn.commit()
        print("Added is_image to patient_messages")
    except Exception as e:
        print(f"is_image: {e}")
        
    # Also update 'message' to be nullable (sqlite doesn't support ALTER COLUMN easily, 
    # but we can try just inserting NULL later since it's defined as nullable in the model now)
    
    print("Migration Done")
