# documents/endpoints.py
import os
import shutil
import time
import mimetypes
import traceback
from typing import List, Optional, Dict # Import Dict
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends, Query
from fastapi.responses import FileResponse
import mysql.connector

# Import PyMuPDF for PDF text extraction
import fitz # PyMuPDF

from database import get_db
from auth import get_current_user, require_role, UserInDB # Import authentication dependency, role checker, and UserInDB model
# Import Document model and add owner_username to it for the response
from documents.models import Document, DocumentVersion, SearchResults # Import models
from documents.utils import sanitize_filename # Import utility function

# Configuration (can move to a separate config file if needed)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True) # Ensure upload directory exists

router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)

def read_text_from_file(file_path: str) -> str:
    """Reads text content from a file, supporting PDF and plain text."""
    try:
        # Check if the file exists and is within the allowed upload directory
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            print(f"Warning: File not found for content search: {file_path}")
            return "" # Return empty string if file not found

        # Security check: Ensure the file path is within the UPLOAD_DIR
        # This prevents directory traversal attacks
        if not os.path.commonpath([os.path.abspath(UPLOAD_DIR), os.path.abspath(file_path)]) == os.path.abspath(UPLOAD_DIR):
             print(f"Security Alert: Attempted to read file outside UPLOAD_DIR during content search: {file_path}")
             return "" # Return empty string for invalid path

        mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type == 'application/pdf':
            try:
                doc = fitz.open(file_path)
                text = ""
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    text += page.get_text()
                doc.close()
                return text
            except Exception as pdf_error:
                print(f"Error reading PDF file {file_path}: {pdf_error}")
                return "" # Return empty string on PDF read error
        elif mime_type and mime_type.startswith('text/'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as text_error:
                print(f"Error reading text file {file_path}: {text_error}")
                return "" # Return empty string on text file read error
        else:
            # Handle other known types or skip unsupported ones
            # For simplicity, we only support PDF and basic text files for content search
            print(f"Info: Skipping content search for unsupported file type: {mime_type} ({file_path})")
            return "" # Skip unsupported types

    except Exception as general_error:
        print(f"Unexpected error in read_text_from_file for {file_path}: {general_error}")
        return "" # Catch any other unexpected errors


# Only users with the 'user' role (Applicants) can upload documents
@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_document_or_version(
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(require_role(["user"])), # Restrict uploads to 'user' role
):
    """
    Uploads a new document (assigning ownership) or a new version of an
    existing document (checking ownership).
    Only users with the 'user' role (Applicants) can upload.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Filename cannot be empty."
        )

    original_filename = file.filename
    file_ext = os.path.splitext(original_filename)[1]
    document_slug = sanitize_filename(original_filename)
    timestamp = int(time.time())
    temp_save_path = os.path.join(UPLOAD_DIR, f"temp_{timestamp}_{original_filename.replace(' ', '_')}")

    try:
        with open(temp_save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        print(f"Error saving file: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e}",
        )
    finally:
        await file.close()

    final_file_path = None # Initialize to None
    try:
        with get_db() as (db, cursor):
            cursor.execute(
                "SELECT id, owner_id FROM documents WHERE title = %s", (document_slug,)
            )
            doc_result = cursor.fetchone()

            document_id: int
            version: int

            if doc_result:
                document_id = doc_result["id"]
                owner_id = doc_result["owner_id"]
                # Ownership check for updating existing documents (still required even with role check on endpoint)
                if owner_id != current_user.id:
                    print(
                        f"AuthZ Error: User {current_user.id} ({current_user.username}) attempted to modify doc {document_id} owned by {owner_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to modify this document",
                    )

                cursor.execute(
                    "SELECT MAX(version) AS max_version FROM document_versions WHERE document_id = %s",
                    (document_id,),
                )
                version_result = cursor.fetchone()
                version = (version_result["max_version"] or 0) + 1

                if description is not None:
                    cursor.execute(
                        "UPDATE documents SET description = %s WHERE id = %s",
                        (description, document_id),
                    )
            else:
                version = 1
                cursor.execute(
                    "INSERT INTO documents (title, description, owner_id, created_at) VALUES (%s, %s, %s, NOW())",
                    (document_slug, description, current_user.id),
                )
                document_id = cursor.lastrowid
                if not document_id:
                    raise Exception("Failed to get last insert ID for new document.")

            final_filename = f"{document_slug}_v{version}_{timestamp}{file_ext}"
            final_file_path = os.path.join(UPLOAD_DIR, final_filename)

            try:
                os.rename(temp_save_path, final_file_path)
            except OSError as e:
                print(f"Error renaming file from {temp_save_path} to {final_file_path}: {e}")
                if os.path.exists(temp_save_path):
                    try:
                        os.remove(temp_save_path)
                        print(f"Cleaned up temporary file: {temp_save_path}")
                    except OSError as rm_err:
                        print(f"Error cleaning up temporary file {temp_save_path} after rename failure: {rm_err}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to finalize file storage: {e}",
                )

            cursor.execute(
                "INSERT INTO document_versions (document_id, version, file_path, uploaded_at) VALUES (%s, %s, %s, NOW())",
                (document_id, version, final_file_path),
            )
            version_id = cursor.lastrowid
            if not version_id:
                raise Exception("Failed to get last insert ID for new version.")

            cursor.execute(
                "UPDATE documents SET latest_file_path = %s WHERE id = %s",
                (final_file_path, document_id),
            )

        return {
            "message": f"File '{original_filename}' uploaded successfully as version {version} for document '{document_slug}'.",
            "document_id": document_id,
            "version_id": version_id,
            "version": version,
            "file_path": final_file_path, # Consider if you want to return the internal file path
            "document_title": document_slug,
        }

    except (mysql.connector.Error, HTTPException) as e:
        if os.path.exists(temp_save_path):
            print(f"Cleaning up temporary file due to DB/HTTP error: {temp_save_path}")
            try:
                os.remove(temp_save_path)
            except OSError as rm_err:
                print(f"Error removing temporary file {temp_save_path}: {rm_err}")
        raise e
    except Exception as e:
        print(f"Unexpected error during DB operations, file rename, or other: {e}")
        traceback.print_exc()
        if os.path.exists(temp_save_path):
            print(f"Cleaning up temporary file due to unexpected error: {temp_save_path}")
            try:
                os.remove(temp_save_path)
            except OSError as rm_err:
                print(f"Error removing temporary file {temp_save_path}: {rm_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {e}",
        )

# Users can only get documents they own
# Recruiters will use a different endpoint to see applicant documents
@router.get("/", response_model=List[Document])
async def get_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInDB = Depends(require_role(["user"])), # Restrict to 'user' role
):
    """Retrieves a list of documents owned by the current user (Applicant)."""
    try:
        with get_db() as (db, cursor):
            query = """
                SELECT id, title, description, latest_file_path, created_at
                FROM documents
                WHERE owner_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (current_user.id, limit, skip))
            docs = cursor.fetchall()
            return docs
    except mysql.connector.Error as e:
        print(f"DB Error fetching documents for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error fetching documents.",
        )
    except Exception as e:
        print(f"Error fetching documents for user {current_user.id}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error fetching documents.",
        )

# --- Endpoint for Recruiters to View Applicant Documents (Include Owner Username) ---
# Use List[Dict] to explicitly allow the extra 'owner_username' field
@router.get("/applicant/", response_model=List[Dict]) # FIX: Changed response_model to List[Dict]
async def get_applicant_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInDB = Depends(require_role(["recruiter"])), # Restrict to 'recruiter' role
):
    """
    Retrieves a list of documents uploaded by users with the 'user' role (Applicants).
    Includes the owner's username. Only accessible by recruiters.
    """
    try:
        with get_db() as (db, cursor):
            # CRITICAL: Ensure u.username AS owner_username is selected here
            query = """
                SELECT d.id, d.title, d.description, d.latest_file_path, d.created_at, u.username AS owner_username
                FROM documents d
                JOIN users u ON d.owner_id = u.id
                WHERE u.role = 'user' -- Filter for documents owned by 'user' role
                ORDER BY d.created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (limit, skip))
            docs = cursor.fetchall()
            # Return as a list of dictionaries to ensure the extra field is kept.
            return docs # Return the raw fetched data

    except mysql.connector.Error as e:
        print(f"DB Error fetching applicant documents for recruiter {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error fetching documents.",
        )
    except Exception as e:
        print(f"Error fetching applicant documents for recruiter {current_user.id}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error fetching documents.",
        )


# Modify search to handle roles: Users search their own, Recruiters search applicant docs
@router.get("/search/", response_model=SearchResults)
async def search_documents(
    query: str,
    search_content: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInDB = Depends(get_current_user), # Authentication check (role handled inside)
):
    """
    Searches for documents based on role:
    - Users ('user' role) search documents they own.
    - Recruiters ('recruiter' role) search documents owned by users with the 'user' role.
    """
    search_term_lower = query.lower()
    matching_documents = []

    try:
        with get_db() as (db, cursor):
            # Determine the base query based on the user's role
            if current_user.role == 'user':
                # User searches their own documents
                base_sql = """
                    SELECT id, title, description, latest_file_path, created_at
                    FROM documents
                    WHERE owner_id = %s
                """
                base_params = (current_user.id,)
            elif current_user.role == 'recruiter':
                # Recruiter searches documents owned by 'user' roles
                # CRITICAL: Ensure u.username AS owner_username is selected for recruiters
                base_sql = """
                    SELECT d.id, d.title, d.description, d.latest_file_path, d.created_at, u.username AS owner_username
                    FROM documents d
                    JOIN users u ON d.owner_id = u.id
                    WHERE u.role = 'user'
                """
                base_params = () # No specific user ID needed for recruiter search

            else:
                 # Handle other roles if necessary, or raise an error
                 raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role for search.")


            if search_content:
                # Fetch all potentially matching documents first based on role criteria
                sql_fetch_all = base_sql + " ORDER BY created_at DESC" # Order before fetching for consistency
                cursor.execute(sql_fetch_all, base_params)
                potential_docs = cursor.fetchall()

                # Filter by content
                for doc in potential_docs:
                    file_path = doc.get('latest_file_path')
                    if file_path:
                        content = read_text_from_file(file_path)
                        if search_term_lower in content.lower():
                            # Append the raw dictionary which includes owner_username for recruiters
                            matching_documents.append(doc)

                # Apply pagination to the content-matched results
                paginated_results = matching_documents[skip : skip + limit]
                # Return the raw list of dictionaries
                return {"results": paginated_results}

            else:
                # Metadata search (title/description)
                sql_metadata_search = base_sql + """
                    AND (LOWER(title) LIKE %s OR LOWER(description) LIKE %s)
                    ORDER BY title
                    LIMIT %s OFFSET %s
                """
                metadata_params = list(base_params) + [f"%{search_term_lower}%", f"%{search_term_lower}%", limit, skip]
                cursor.execute(sql_metadata_search, tuple(metadata_params))
                results = cursor.fetchall()
                # Return the raw list of dictionaries
                return {"results": results}

    except mysql.connector.Error as e:
        print(f"DB Error searching documents for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error searching documents.",
        )
    except HTTPException:
         raise # Re-raise explicit HTTPExceptions (like the 403)
    except Exception as e:
        print(f"Error searching documents for user {current_user.id}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error searching documents.",
        )

# Modify version access: Allow owner OR recruiter if owner is 'user'
@router.get("/{document_id}/versions/")
async def get_document_versions(
    document_id: int,
    current_user: UserInDB = Depends(get_current_user), # Authentication check (role handled inside)
):
    """
    Retrieves details and versions for a specific document.
    Accessible by the document owner OR by a recruiter if the owner has the 'user' role.
    """
    try:
        with get_db() as (db, cursor):
            # Modified query to join with users table and select owner_role
            cursor.execute(
                "SELECT d.id, d.title, d.description, d.latest_file_path, d.created_at, d.owner_id, u.role AS owner_role FROM documents d JOIN users u ON d.owner_id = u.id WHERE d.id = %s",
                (document_id,),
            )
            doc = cursor.fetchone()
            if not doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with ID {document_id} not found.",
                )

            # Access Control Check: Owner OR Recruiter viewing user's doc
            is_owner = doc["owner_id"] == current_user.id
            is_recruiter_viewing_user_doc = (
                current_user.role == 'recruiter' and doc["owner_role"] == 'user'
            )

            if not (is_owner or is_recruiter_viewing_user_doc):
                print(
                    f"AuthZ Error: User {current_user.id} ({current_user.username}, role={current_user.role}) attempted to view versions for doc {document_id} owned by {doc['owner_id']} (role={doc['owner_role']})"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this document's versions",
                )

            cursor.execute(
                "SELECT id, version, file_path, uploaded_at FROM document_versions WHERE document_id = %s ORDER BY version DESC",
                (document_id,),
            )
            versions = cursor.fetchall()
            latest_version = max([v["version"] for v in versions]) if versions else 0
            # Create a Document model instance, excluding owner_id and owner_role
            doc_details = Document(**{k: v for k, v in doc.items() if k != "owner_id" and k != "owner_role"})
            versions_list = [DocumentVersion(**v) for v in versions]

            return {
                "document": doc_details,
                "versions": versions_list,
                "latest_version": latest_version
            }
    except mysql.connector.Error as e:
        print(
            f"DB Error fetching versions for doc {document_id}, user {current_user.id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error fetching versions.",
        )
    except HTTPException:
        raise
    except Exception as e:
        print(
            f"Error fetching versions for doc {document_id}, user {current_user.id}: {e}"
        )
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error fetching versions.",
        )

# Modify download access: Allow owner OR recruiter if owner is 'user'
@router.get("/{document_id}/versions/{version_number}/download")
async def download_document_version(
    document_id: int,
    version_number: int,
    current_user: UserInDB = Depends(get_current_user) # Authentication check (role handled inside)
):
    """
    Downloads a specific document version.
    Accessible by the document owner OR by a recruiter if the owner has the 'user' role.
    """
    try:
        with get_db() as (db, cursor):
            # Modified query to join with users table and select owner_role
            cursor.execute(
                """
                SELECT dv.file_path, d.title, d.owner_id, u.role AS owner_role
                FROM document_versions dv
                JOIN documents d ON dv.document_id = d.id
                JOIN users u ON d.owner_id = u.id
                WHERE dv.document_id = %s AND dv.version = %s
                """,
                (document_id, version_number)
            )
            version_record = cursor.fetchone()
            if not version_record:
                cursor.execute("SELECT id FROM documents WHERE id = %s", (document_id,))
                doc_exists = cursor.fetchone()
                if not doc_exists:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID {document_id} not found.")
                else:
                     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version {version_number} for document ID {document_id} not found.")

            # Access Control Check: Owner OR Recruiter viewing user's doc
            is_owner = version_record['owner_id'] == current_user.id
            is_recruiter_viewing_user_doc = (
                current_user.role == 'recruiter' and version_record['owner_role'] == 'user'
            )

            if not (is_owner or is_recruiter_viewing_user_doc):
                 print(f"AuthZ Error: User {current_user.id} ({current_user.username}, role={current_user.role}) attempted to download version {version_number} for doc {document_id} owned by {version_record['owner_id']} (role={version_record['owner_role']})")
                 raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to download this document version")

            file_path = version_record['file_path']
            if not os.path.commonpath([os.path.abspath(UPLOAD_DIR), os.path.abspath(file_path)]) == os.path.abspath(UPLOAD_DIR):
                 print(f"Security Alert: Attempted to access file outside UPLOAD_DIR: {file_path}")
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path.")

            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                 print(f"Error: File not found on disk at path: {file_path} (DB record exists)")
                 raise HTTPException(
                     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                     detail="File record exists but file not found on server."
                 )

            base_filename = os.path.basename(file_path)
            suggested_filename = base_filename

            media_type, _ = mimetypes.guess_type(file_path)
            media_type = media_type or 'application/octet-stream'

            return FileResponse(
                path=file_path,
                filename=suggested_filename,
                media_type=media_type
            )

    except mysql.connector.Error as e:
        print(f"DB Error downloading version {version_number} for doc {document_id}, user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error during download.")
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error downloading version {version_number} for doc {document_id}, user {current_user.id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error during download.")
