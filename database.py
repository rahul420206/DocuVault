# database.py
import mysql.connector
from contextlib import contextmanager

@contextmanager
def get_db():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="job_tracker"  # replace with your DB name
    )
    try:
        yield db
    finally:
        db.close()
