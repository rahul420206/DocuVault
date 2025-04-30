# database.py
import mysql.connector
from contextlib import contextmanager
import os

# --- Database Configuration ---
# Replace with your actual database credentials
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "password" # Use environment variables in production!
DB_NAME = "job_tracker"

@contextmanager
def get_db():
    """Provides a database connection and cursor with transaction handling."""
    db = None
    cursor = None
    try:
        db = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        # Using dictionary=True makes fetching results easier (access by column name)
        cursor = db.cursor(dictionary=True)
        print("DB connection opened.")
        yield db, cursor # Yield connection and cursor
        print("Committing transaction.")
        db.commit() # Commit if the 'with' block succeeded
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        if db:
            print("Rolling back transaction due to DB error.")
            db.rollback()
        raise # Re-raise the exception so FastAPI can handle it
    except Exception as e:
        print(f"Non-DB Error: {e}")
        if db:
            print("Rolling back transaction due to non-DB error.")
            db.rollback()
        raise # Re-raise
    finally:
        if cursor:
            cursor.close()
            print("DB cursor closed.")
        if db and db.is_connected():
            db.close()
            print("DB connection closed.")