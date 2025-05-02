import os
import shutil
import time
import re
import traceback
from typing import List, Optional, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, EmailStr
from database import get_db
import mysql.connector
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import mimetypes

# Import the CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware

os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:8000"

app = FastAPI(title="Document Management System API (mysql.connector Version)")
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
SECRET_KEY = "your-super-secret-key-that-needs-to-be-changed"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: int
    role: Optional[str]

    class Config:
        from_attributes = True

class UserInDBInternal(UserInDB):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class DocumentVersion(BaseModel):
    id: int
    version: int
    file_path: str
    uploaded_at: datetime

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        print(f"Decoded JWT payload: {payload}")  # Debug log
        if username is None:
            print(f"JWT token missing 'sub' claim: {token[:20]}...")
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        print(f"JWT decode error: {str(e)}, token: {token[:20]}...")
        raise credentials_exception

    try:
        with get_db() as (db, cursor):
            cursor.execute(
                "SELECT id, username, role FROM users WHERE username = %s",
                (token_data.username,)
            )
            user_data = cursor.fetchone()
            print(f"DB query result for username '{token_data.username}': {user_data}")  # Debug log
            if user_data is None:
                print(f"User '{token_data.username}' from token not found in DB.")
                raise credentials_exception
            user = UserInDB(**user_data)
            return user
    except mysql.connector.Error as e:
        print(f"DB error fetching user '{token_data.username}': {e}")
        raise HTTPException(status_code=500, detail="Database error during authentication.")
    except Exception as e:
        print(f"Unexpected error fetching user '{token_data.username}': {e}")
        raise credentials_exception
    
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Logs in a user and returns an access token."""
    try:
        with get_db() as (db, cursor):
            cursor.execute(
                "SELECT id, username, password, role FROM users WHERE username = %s",
                (form_data.username,)
            )
            user_data = cursor.fetchone()
            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user_in_db = UserInDBInternal(**user_data)
            if not verify_password(form_data.password, user_in_db.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user_in_db.username}, expires_delta=access_token_expires
            )
            return {"access_token": access_token, "token_type": "bearer"}

    except mysql.connector.Error as e:
        print(f"DB Error during login for user {form_data.username}: {e}")
        raise HTTPException(status_code=500, detail="Login failed due to database error.")
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error during login for user {form_data.username}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during login."
        )

@app.post("/users/signup", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Registers a new user."""
    hashed_password = get_password_hash(user.password)
    try:
        with get_db() as (db, cursor):
            cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered",
                )
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (user.username, hashed_password, "user"),
            )
            user_id = cursor.lastrowid
            if not user_id:
                raise Exception("Failed to get ID for new user.")
            cursor.execute("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
            new_user_data = cursor.fetchone()
            if not new_user_data:
                raise Exception("Failed to fetch newly created user data.")

            return UserInDB(**new_user_data)

    except mysql.connector.Error as e:
        print(f"DB Error during signup for user {user.username}: {e}")
        if e.errno == 1062:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered.",
            )
        raise HTTPException(
            status_code=500, detail="User registration failed due to database error."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error during signup for user {user.username}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during signup."
        )

@app.get("/users/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    """Returns the details of the currently authenticated user."""
    return current_user

def sanitize_filename(filename: str) -> str:
    """Removes extension and replaces non-alphanumeric characters with underscores."""
    base = os.path.splitext(filename)[0]
    sanitized = re.sub(r"[^\w\-]+", "_", base)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized if sanitized else "untitled"

@app.post("/documents/", status_code=status.HTTP_201_CREATED)
async def upload_document_or_version(
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Uploads a new document (assigning ownership) or a new version of an
    existing document (checking ownership).
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Filename cannot be empty."
        )

    original_filename = file.filename
    file_ext = os.path.splitext(original_filename)[1]
    document_slug = sanitize_filename(original_filename)
    timestamp = int(time.time())
    temp_save_path = os.path.join(UPLOAD_DIR, f"temp_{timestamp}_{original_filename}")
    try:
        print(f"Attempting to save file to temporary path: {temp_save_path}")
        with open(temp_save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File temporarily saved to: {temp_save_path}")
    except Exception as e:
        print(f"Error saving file: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e}",
        )
    finally:
        await file.close()
    final_file_path = None
    try:
        with get_db() as (db, cursor):
            print(f"Checking database for document with title: {document_slug}")
            cursor.execute(
                "SELECT id, owner_id FROM documents WHERE title = %s", (document_slug,)
            )
            doc_result = cursor.fetchone()

            document_id: int
            version: int

            if doc_result:
                document_id = doc_result["id"]
                owner_id = doc_result["owner_id"]
                if owner_id != current_user.id:
                    print(
                        f"AuthZ Error: User {current_user.id} ({current_user.username}) attempted to modify doc {document_id} owned by {owner_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to modify this document",
                    )

                print(
                    f"User {current_user.id} authorized for doc {document_id}. Fetching max version."
                )
                cursor.execute(
                    "SELECT MAX(version) AS max_version FROM document_versions WHERE document_id = %s",
                    (document_id,),
                )
                version_result = cursor.fetchone()
                version = (version_result["max_version"] or 0) + 1
                print(f"Determined next version: {version}")
                if description is not None:
                    print(f"Updating description for document ID: {document_id}")
                    cursor.execute(
                        "UPDATE documents SET description = %s WHERE id = %s",
                        (description, document_id),
                    )
            else:
                version = 1
                print(
                    f"Document not found. Creating new document '{document_slug}' owned by user {current_user.id}."
                )
                cursor.execute(
                    "INSERT INTO documents (title, description, owner_id, created_at) VALUES (%s, %s, %s, NOW())",
                    (document_slug, description, current_user.id),
                )
                document_id = cursor.lastrowid
                if not document_id:
                    raise Exception("Failed to get last insert ID for new document.")
                print(f"New document created (ID: {document_id}). Version will be {version}")
            final_filename = f"{document_slug}_v{version}_{timestamp}{file_ext}"
            final_file_path = os.path.join(UPLOAD_DIR, final_filename)
            try:
                print(f"Renaming temporary file '{temp_save_path}' to '{final_file_path}'")
                os.rename(temp_save_path, final_file_path)
            except OSError as e:
                print(
                    f"Error renaming file from {temp_save_path} to {final_file_path}: {e}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to finalize file storage: {e}",
                )
            print(
                f"Inserting version record: doc_id={document_id}, version={version}, path={final_file_path}"
            )
            cursor.execute(
                "INSERT INTO document_versions (document_id, version, file_path, uploaded_at) VALUES (%s, %s, %s, NOW())",
                (document_id, version, final_file_path),
            )
            version_id = cursor.lastrowid
            if not version_id:
                raise Exception("Failed to get last insert ID for new version.")
            print(
                f"Updating latest_file_path for document ID {document_id} to '{final_file_path}'"
            )
            cursor.execute(
                "UPDATE documents SET latest_file_path = %s WHERE id = %s",
                (final_file_path, document_id),
            )

            return {
                "message": f"File '{original_filename}' uploaded successfully as version {version} for document '{document_slug}'.",
                "document_id": document_id,
                "version_id": version_id,
                "version": version,
                "file_path": final_file_path,
                "document_title": document_slug,
            }

    except (mysql.connector.Error, HTTPException) as e:
        if os.path.exists(temp_save_path):
            print(f"Cleaning up temporary file due to error: {temp_save_path}")
            try:
                os.remove(temp_save_path)
            except OSError as rm_err:
                print(f"Error removing temporary file {temp_save_path}: {rm_err}")
        raise e
    except Exception as e:
        print(f"Unexpected error during DB operations or file rename: {e}")
        traceback.print_exc()
        if os.path.exists(temp_save_path):
            print(f"Cleaning up temporary file due to error: {temp_save_path}")
            try:
                os.remove(temp_save_path)
            except OSError as rm_err:
                print(f"Error removing temporary file {temp_save_path}: {rm_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {e}",
        )

class Document(BaseModel):
    id: int
    title: str
    description: Optional[str]
    latest_file_path: Optional[str]
    created_at: datetime

from fastapi import Query
@app.get("/documents/", response_model=List[Document])
async def get_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInDB = Depends(get_current_user),
):
    """Retrieves a list of documents owned by the current user."""
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

class SearchResults(BaseModel):
    results: List[Document]

@app.get("/documents/search/", response_model=SearchResults)
async def search_documents(
    query: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInDB = Depends(get_current_user),
):
    search_term = f"%{query.lower()}%"
    try:
        with get_db() as (db, cursor):
            sql = """
                SELECT id, title, description, latest_file_path, created_at
                FROM documents
                WHERE owner_id = %s AND (LOWER(title) LIKE %s OR LOWER(description) LIKE %s)
                ORDER BY title
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (current_user.id, search_term, search_term, limit, skip))
            results = cursor.fetchall()
            return {"results": results}
    except mysql.connector.Error as e:
        print(f"DB Error searching documents for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error searching documents.",
        )
    except Exception as e:
        print(f"Error searching documents for user {current_user.id}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error searching documents.",
        )

@app.get("/documents/{document_id}/versions/")
async def get_document_versions(
    document_id: int,
    current_user: UserInDB = Depends(get_current_user),
):
    """Retrieves details and versions for a specific document owned by the current user."""
    try:
        with get_db() as (db, cursor):
            cursor.execute(
                "SELECT id, title, description, latest_file_path, created_at, owner_id FROM documents WHERE id = %s",
                (document_id,),
            )
            doc = cursor.fetchone()
            if not doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with ID {document_id} not found.",
                )
            if doc["owner_id"] != current_user.id:
                print(
                    f"AuthZ Error: User {current_user.id} attempted to view versions for doc {document_id} owned by {doc['owner_id']}"
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
            # Get latest version number
            latest_version = max([v["version"] for v in versions]) if versions else 0
            doc_details = {k: v for k, v in doc.items() if k != "owner_id"}
            print(f"Fetched versions for doc {document_id}: {len(versions)} versions, latest: {latest_version}")
            return {
                "document": doc_details,
                "versions": versions,
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
    
@app.get("/documents/{document_id}/versions/{version_number}/download")
async def download_document_version(
    document_id: int,
    version_number: int,
    current_user: UserInDB = Depends(get_current_user)
):
    """Downloads a specific document version, checking ownership."""
    try:
        with get_db() as (db, cursor):
            cursor.execute(
                """
                SELECT dv.file_path, d.title, d.owner_id
                FROM document_versions dv
                JOIN documents d ON dv.document_id = d.id
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
            if version_record['owner_id'] != current_user.id:
                 print(f"AuthZ Error: User {current_user.id} attempted to download version {version_number} for doc {document_id} owned by {version_record['owner_id']}")
                 raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to download this document version")
            file_path = version_record['file_path']
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
            print(f"Serving file to user {current_user.id}: {file_path} as {media_type}")
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

app.mount("/static", StaticFiles(directory="static"), name="static")

# Add this to enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return html_content

@app.get("/dashboard.html", response_class=HTMLResponse)
async def dashboard():
    with open("static/dashboard.html", "r") as f:
        dashboard_content = f.read()
    return dashboard_content
