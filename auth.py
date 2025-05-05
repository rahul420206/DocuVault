# auth.py
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
import mysql.connector
from database import get_db

# Import models from users
from users.models import UserInDB, UserInDBInternal, Token, TokenData, UserCreate

# Configuration (can move to a separate config file if needed)
SECRET_KEY = os.getenv("SECRET_KEY", "5b182e8d53509cc4a2b18b3a991ea9acc3a06a798db0686b20faa87e0598f103")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440)) # Use the correct value

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token dependency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token") # Assuming /token is the login endpoint

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """Dependency to get the current authenticated user from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    try:
        with get_db() as (db, cursor):
            cursor.execute(
                "SELECT id, username, role FROM users WHERE username = %s",
                (token_data.username,)
            )
            user_data = cursor.fetchone()
            if user_data is None:
                raise credentials_exception
            # Ensure user_data is a dictionary or map it correctly
            user = UserInDB(**user_data)
            return user
    except mysql.connector.Error as e:
        print(f"DB error fetching user '{token_data.username}': {e}")
        raise HTTPException(status_code=500, detail="Database error during authentication.")
    except Exception as e:
        print(f"Unexpected error fetching user '{token_data.username}': {e}")
        import traceback
        traceback.print_exc()
        raise credentials_exception

# --- Dependency for Role Checking ---
def require_role(roles: List[str]):
    """
    Dependency to check if the current user has one of the required roles.
    Usage: Depends(require_role(["admin", "editor"]))
    """
    async def role_checker(current_user: UserInDB = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User with role '{current_user.role}' is not authorized. Required roles: {', '.join(roles)}",
            )
        return current_user # Return the user object if role is valid

    return role_checker

# This endpoint remains here as it's the entry point for obtaining tokens
# It uses verify_password and create_access_token from this file
# and interacts with the database via get_db
router = APIRouter()

@router.post("/token", response_model=Token)
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

            user_in_db = UserInDBInternal(**user_data) # Use internal model with password
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
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during login."
        )
