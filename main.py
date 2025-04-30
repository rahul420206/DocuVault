# main.py
import os
import shutil
import time
import re # For sanitizing filename
import traceback # For detailed error logging
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException

# Import the database context manager
from database import get_db
import mysql.connector # Import Error class

# --- FastAPI App ---
app = FastAPI(title="Document Management System API (mysql.connector Version)")

# --- Configuration ---
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Helper Function (same as before) ---
def sanitize_filename(filename: str) -> str:
    """Removes extension and replaces non-alphanumeric characters with underscores."""
    base = os.path.splitext(filename)[0]
    sanitized = re.sub(r'[^\w\-]+', '_', base)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized if sanitized else "untitled"

# --- API Endpoints ---

@app.post("/documents/", status_code=201)
async def upload_document_or_version(
    description: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    """
    Uploads a new document or a new version of an existing document
    using mysql.connector. Identification is based on the sanitized filename.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    original_filename = file.filename
    file_ext = os.path.splitext(original_filename)[1]
    document_slug = sanitize_filename(original_filename)

    # Construct potential file path *before* DB transaction
    # We determine the actual version number inside the transaction
    timestamp = int(time.time())
    # Temporary name structure, version will be determined later
    temp_filename_base = f"{document_slug}_v<VERSION>_{timestamp}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, "determining_version_" + original_filename) # Placeholder path initially

    # --- Save file FIRST ---
    # This avoids DB rollback issues if file saving fails after DB changes were made.
    try:
        print(f"Attempting to save file to temporary path: {file_path}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File temporarily saved to: {file_path}")
    except Exception as e:
        print(f"Error saving file: {e}")
        traceback.print_exc()
        # No DB changes made yet, just report file error
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    finally:
         await file.close() # Ensure file handle is closed

    # --- Database Operations ---
    try:
        with get_db() as (db, cursor):
            # Step 1: Check if document with this slug exists
            print(f"Checking database for document with title: {document_slug}")
            cursor.execute("SELECT id FROM documents WHERE title = %s", (document_slug,))
            doc_result = cursor.fetchone() # Returns dict or None

            document_id: int
            version: int

            if doc_result:
                # Document exists - create new version
                document_id = doc_result['id']
                print(f"Document found (ID: {document_id}). Fetching max version.")

                # Get the latest version number
                cursor.execute(
                    "SELECT MAX(version) AS max_version FROM document_versions WHERE document_id = %s",
                    (document_id,)
                )
                version_result = cursor.fetchone() # Dict with 'max_version' key
                version = (version_result['max_version'] or 0) + 1
                print(f"Determined next version: {version}")

                # Update description if provided
                if description is not None:
                    print(f"Updating description for document ID: {document_id}")
                    cursor.execute(
                        "UPDATE documents SET description = %s WHERE id = %s",
                        (description, document_id)
                    )
            else:
                # Document does not exist - create new document and version 1
                version = 1
                print(f"Document not found. Creating new document '{document_slug}'.")
                cursor.execute(
                    "INSERT INTO documents (title, description, created_at) VALUES (%s, %s, NOW())",
                    (document_slug, description)
                )
                document_id = cursor.lastrowid # Get the ID of the inserted row
                if not document_id:
                     raise Exception("Failed to get last insert ID for new document.")
                print(f"New document created (ID: {document_id}). Version will be {version}")


            # Step 2: Determine final versioned filename and rename the saved file
            final_filename = f"{document_slug}_v{version}_{timestamp}{file_ext}"
            final_file_path = os.path.join(UPLOAD_DIR, final_filename)
            try:
                print(f"Renaming temporary file '{file_path}' to '{final_file_path}'")
                os.rename(file_path, final_file_path)
            except OSError as e:
                print(f"Error renaming file from {file_path} to {final_file_path}: {e}")
                # If renaming fails, we need to let the transaction rollback
                raise HTTPException(status_code=500, detail=f"Failed to finalize file storage: {e}")

            # Step 3: Create new version entry in database
            print(f"Inserting version record: doc_id={document_id}, version={version}, path={final_file_path}")
            cursor.execute(
                "INSERT INTO document_versions (document_id, version, file_path, uploaded_at) VALUES (%s, %s, %s, NOW())",
                (document_id, version, final_file_path)
            )
            version_id = cursor.lastrowid # Get the ID of the new version entry

            # Step 4: Update the latest_file_path in the main document record
            print(f"Updating latest_file_path for document ID {document_id} to '{final_file_path}'")
            cursor.execute(
                "UPDATE documents SET latest_file_path = %s WHERE id = %s",
                (final_file_path, document_id)
            )

            # Commit happens automatically when 'with' block exits without error

            return {
                "message": f"File '{original_filename}' uploaded successfully as version {version} for document '{document_slug}'.",
                "document_id": document_id,
                "version_id": version_id,
                "version": version,
                "file_path": final_file_path,
                "document_title": document_slug
            }

    except (mysql.connector.Error, HTTPException) as e:
        # Database errors handled by get_db, HTTPException raised directly
        # Clean up the temporarily saved file if it still exists under the temp name
        if os.path.exists(file_path):
            print(f"Cleaning up temporary file due to error: {file_path}")
            try:
                os.remove(file_path)
            except OSError as rm_err:
                print(f"Error removing temporary file {file_path}: {rm_err}")
        raise e # Re-raise the original exception
    except Exception as e:
        # Catch-all for unexpected errors during DB phase
        print(f"Unexpected error during DB operations or file rename: {e}")
        traceback.print_exc()
        # Clean up the temporarily saved file if it still exists under the temp name
        if os.path.exists(file_path):
            print(f"Cleaning up temporary file due to error: {file_path}")
            try:
                os.remove(file_path)
            except OSError as rm_err:
                print(f"Error removing temporary file {file_path}: {rm_err}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")


@app.get("/documents/")
async def get_documents(skip: int = 0, limit: int = 100):
    """Retrieves a list of all documents using mysql.connector."""
    try:
        with get_db() as (db, cursor):
            query = "SELECT id, title, description, latest_file_path, created_at FROM documents ORDER BY created_at DESC LIMIT %s OFFSET %s"
            cursor.execute(query, (limit, skip))
            docs = cursor.fetchall() # List of dictionaries
            return docs
    except mysql.connector.Error as e:
        print(f"DB Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail="Database error fetching documents.")
    except Exception as e:
        print(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail="Server error fetching documents.")


@app.get("/documents/search/")
async def search_documents(query: str):
    """Searches for documents by title or description using mysql.connector."""
    search_term = f"%{query}%"
    try:
        with get_db() as (db, cursor):
            sql = "SELECT id, title, description, latest_file_path, created_at FROM documents WHERE title LIKE %s OR description LIKE %s ORDER BY title"
            cursor.execute(sql, (search_term, search_term))
            results = cursor.fetchall() # List of dictionaries

            if not results:
                 raise HTTPException(status_code=404, detail=f"No documents found matching '{query}'.")

            return {"results": results}
    except mysql.connector.Error as e:
        print(f"DB Error searching documents: {e}")
        raise HTTPException(status_code=500, detail="Database error searching documents.")
    except HTTPException:
        raise # Re-raise 404 if applicable
    except Exception as e:
        print(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail="Server error searching documents.")


@app.get("/documents/{document_id}/versions/")
async def get_document_versions(document_id: int):
    """Retrieves a specific document and all its versions using mysql.connector."""
    try:
        with get_db() as (db, cursor):
            # Fetch document details
            cursor.execute("SELECT id, title, description, latest_file_path, created_at FROM documents WHERE id = %s", (document_id,))
            doc = cursor.fetchone() # Dictionary or None

            if not doc:
                raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found.")

            # Fetch associated versions
            cursor.execute(
                "SELECT id, version, file_path, uploaded_at FROM document_versions WHERE document_id = %s ORDER BY version ASC",
                (document_id,)
            )
            versions = cursor.fetchall() # List of dictionaries

            return {
                "document": doc,
                "versions": versions
            }
    except mysql.connector.Error as e:
        print(f"DB Error fetching document versions: {e}")
        raise HTTPException(status_code=500, detail="Database error fetching versions.")
    except HTTPException:
        raise # Re-raise 404 if applicable
    except Exception as e:
        print(f"Error fetching document versions: {e}")
        raise HTTPException(status_code=500, detail="Server error fetching versions.")

@app.get("/")
def root():
    return {"message": "Document Management API (mysql.connector Version) is running."}

# --- Add if running directly with uvicorn ---
# if __name__ == "__main__":
#    import uvicorn
#    uvicorn.run(app, host="0.0.0.0", port=8000)