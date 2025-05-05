# users/endpoints.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
import mysql.connector
from typing import List
from database import get_db
from users.models import UserCreate, UserInDB
from auth import get_password_hash, get_current_user, require_role, UserInDB
import traceback

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# No role restriction on signup, anyone can sign up
@router.post("/signup", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Registers a new user."""
    # Validate role - only allow 'user' and 'recruiter'
    if user.role not in ["user", "recruiter"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'user' or 'recruiter'",
        )
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
                (user.username, hashed_password, user.role), # Use provided role
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
        if e.errno == 1062: # MySQL error code for duplicate entry
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

# Anyone authenticated can get their own user details
@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    """Returns the details of the currently authenticated user."""
    return current_user

# --- Endpoint for Recruiters to View ONLY Users (Applicants) ---
# This endpoint is restricted to users with the 'recruiter' role.
@router.get("/", response_model=List[UserInDB])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInDB = Depends(require_role(["recruiter"])) # Restrict to recruiters
):
    """
    Retrieves a list of all users with the 'user' role (Applicants).
    This endpoint is only accessible by users with the 'recruiter' role.
    Can be used by recruiters to see the list of applicants (users).
    """
    try:
        with get_db() as (db, cursor):
            # FIX: Ensure WHERE clause filters for role = 'user'
            query = """
                SELECT id, username, role
                FROM users
                WHERE role = 'user' -- Explicitly filter for 'user' role
                ORDER BY username
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (limit, skip))
            users_data = cursor.fetchall()
            # Convert fetched data (dictionaries) to UserInDB models
            return [UserInDB(**user_data) for user_data in users_data]
    except mysql.connector.Error as e:
        print(f"DB Error fetching all users for recruiter {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Database error fetching users.")
    except Exception as e:
        print(f"Error fetching all users for recruiter {current_user.id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Server error fetching users.")
