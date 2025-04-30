from datetime import datetime
import os
import time
import shutil
from contextlib import contextmanager  # Import contextmanager
import mysql.connector  # Import mysql.connector
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from models import Document, DocumentVersion
import traceback
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from database import get_db

# Dependency to get the database session
@contextmanager
def get_db():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="job_tracker"
    )
    cursor = db.cursor(dictionary=True)
    try:
        yield db, cursor
    finally:
        cursor.close()
        db.close()

app = FastAPI()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/smart_upload/")
async def smart_upload(
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...)
):
    timestamp = int(time.time())
    file_ext = os.path.splitext(file.filename)[1]
    
    with get_db() as (db, cursor):
        # Step 1: Check if document exists
        cursor.execute("SELECT id FROM documents WHERE title = %s", (title,))
        doc = cursor.fetchone()

        if doc:
            document_id = doc['id']
        else:
            # Step 2: Insert into documents
            cursor.execute(
                "INSERT INTO documents (title, description, file_path) VALUES (%s, %s, %s)",
                (title, description, "")
            )
            db.commit()
            document_id = cursor.lastrowid

        # Step 3: Get the current version number
        cursor.execute(
            "SELECT MAX(version) AS max_version FROM document_versions WHERE document_id = %s",
            (document_id,)
        )
        result = cursor.fetchone()
        version = (result["max_version"] or 0) + 1

        # Step 4: Construct versioned filename
        safe_title = title.replace(" ", "_")
        file_path = f"{UPLOAD_DIR}/{safe_title}_v{version}_{timestamp}_{file.filename}"
        
        # Save the file
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Step 5: Update latest file path in documents
        cursor.execute(
            "UPDATE documents SET file_path = %s WHERE id = %s",
            (file_path, document_id)
        )

        # Step 6: Insert new version
        cursor.execute(
            "INSERT INTO document_versions (document_id, version, file_path) VALUES (%s, %s, %s)",
            (document_id, version, file_path)
        )
        db.commit()

    return {"message": "File uploaded successfully", "document_id": document_id, "version": version}


@app.get("/documents")
def get_documents():
    with get_db() as db:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
        docs = cursor.fetchall()
        return docs

@app.get("/")
def root():
    return {"message": "Document Management API is running."}


from fastapi import HTTPException

@app.post("/upload-version")
async def upload_version(
    document_id: int = Form(...),
    file: UploadFile = None
):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with get_db() as db:
        cursor = db.cursor()

        # 🔍 Check if document exists
        cursor.execute("SELECT id FROM documents WHERE id = %s", (document_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Document ID not found")

        # 🧮 Get latest version number
        cursor.execute(
            "SELECT MAX(version) FROM document_versions WHERE document_id = %s",
            (document_id,)
        )
        result = cursor.fetchone()
        next_version = (result[0] or 0) + 1

        # 💾 Insert new version
        cursor.execute(
            "INSERT INTO document_versions (document_id, version, file_path) VALUES (%s, %s, %s)",
            (document_id, next_version, file_path)
        )
        db.commit()

    return {"message": f"Version {next_version} uploaded successfully."}

@app.get("/search")
def search_documents(query: str):
    with get_db() as db:
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM documents WHERE title LIKE %s OR description LIKE %s",
            (f"%{query}%", f"%{query}%")
        )
        results = cursor.fetchall()

        if not results:
            raise HTTPException(status_code=404, detail="No documents found.")

        return {"results": results}

@app.get("/document/{document_id}/versions")
def get_document_versions(document_id: int):
    with get_db() as db:
        cursor = db.cursor(dictionary=True)

        # Check if document exists
        cursor.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        doc = cursor.fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        # Fetch versions
        cursor.execute(
            "SELECT version, file_path, uploaded_at FROM document_versions WHERE document_id = %s ORDER BY version ASC",
            (document_id,)
        )
        versions = cursor.fetchall()

        return {
            "document": doc,
            "versions": versions
        }
