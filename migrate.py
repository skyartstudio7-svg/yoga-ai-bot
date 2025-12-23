from database.database import engine
from sqlalchemy import text

def migrate():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN reminder_frequency VARCHAR(50) DEFAULT 'daily'"))
            conn.commit()
            print("Successfully added reminder_frequency column")
    except Exception as e:
        print(f"Error or column already exists: {e}")

if __name__ == "__main__":
    migrate()
