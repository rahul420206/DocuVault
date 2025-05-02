    # # Add these imports to main.py
    # from fastapi import FastAPI, Depends, status, HTTPException
    # from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
    # from passlib.context import CryptContext
    # from jose import JWTError, jwt
    # from datetime import datetime, timedelta, timezone # Ensure timezone is imported
    # from pydantic import BaseModel, EmailStr # For data validation
    # from typing import Optional # For optional type hints

    # # --- FastAPI Application ---
    # app = FastAPI()

    # # --- Security Configuration ---
    # # !!! CHANGE THIS IN PRODUCTION !!! Use a strong, randomly generated secret key
    # # You can generate one using: openssl rand -hex 32
    # SECRET_KEY = "your-super-secret-key-that-needs-to-be-changed"
    # ALGORITHM = "HS256"
    # ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Token validity period

    # # --- Password Hashing ---
    # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # # --- OAuth2 Scheme ---
    # # tokenUrl should match the path operation where the client gets the token
    # oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    # # --- Pydantic Models for Auth ---
    # class UserBase(BaseModel):
    #     username: str
    #     email: EmailStr

    # class UserCreate(UserBase):
    #     password: str

    # class UserInDB(UserBase):
    #     id: int
    #     is_active: bool
    #     # hashed_password: str # Don't expose hashed password outwards

    #     class Config:
    #         from_attributes = True # For SQLAlchemy ORM mode, works ok here too

    # class Token(BaseModel):
    #     access_token: str
    #     token_type: str

    # class TokenData(BaseModel):
    #     username: Optional[str] = None

    # # --- Database Dependency ---
    # import mysql.connector
    # from contextlib import contextmanager

    # @contextmanager
    # def get_db():
    #     """Dependency to get a database connection."""
    #     connection = mysql.connector.connect(
    #         host="your-database-host",
    #         user="your-database-user",
    #         password="your-database-password",
    #         database="your-database-name"
    #     )
    #     cursor = connection.cursor(dictionary=True)
    #     try:
    #         yield connection, cursor
    #     finally:
    #         cursor.close()
    #         connection.close()

    # # --- Authentication Helper Functions ---

    # def verify_password(plain_password: str, hashed_password: str) -> bool:
    #     return pwd_context.verify(plain_password, hashed_password)

    # def get_password_hash(password: str) -> str:
    #     return pwd_context.hash(password)

    # def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    #     to_encode = data.copy()
    #     if expires_delta:
    #         expire = datetime.now(timezone.utc) + expires_delta
    #     else:
    #         # Default expiration time
    #         expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    #     to_encode.update({"exp": expire})
    #     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    #     return encoded_jwt

    # # --- Dependency to Get Current User ---

    # async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    #     credentials_exception = HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Could not validate credentials",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    #     try:
    #         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    #         username: str = payload.get("sub")
    #         if username is None:
    #             raise credentials_exception
    #         token_data = TokenData(username=username)
    #     except JWTError:
    #         print(f"JWT Error decoding token: {token}")
    #         raise credentials_exception

    #     # Fetch user details from DB
    #     try:
    #         with get_db() as (db, cursor):
    #             cursor.execute("SELECT id, username, email, is_active FROM users WHERE username = %s", (token_data.username,))
    #             user_data = cursor.fetchone()
    #             if user_data is None:
    #                 print(f"User '{token_data.username}' from token not found in DB.")
    #                 raise credentials_exception
    #             # Convert DB dict to Pydantic model
    #             user = UserInDB(**user_data)
    #             if not user.is_active:
    #                 print(f"User '{token_data.username}' is inactive.")
    #                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    #             return user
    #     except mysql.connector.Error as e:
    #         print(f"DB error fetching user '{token_data.username}': {e}")
    #         raise HTTPException(status_code=500, detail="Database error during authentication.")
    #     except Exception as e:
    #         print(f"Unexpected error fetching user '{token_data.username}': {e}")
    #         raise credentials_exception # Treat unexpected errors as auth failures

    # # --- Authentication Endpoints --- (Add these to main.py)

    # @app.post("/token", response_model=Token)
    # async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    #     """Logs in a user and returns an access token."""
    #     try:
    #         with get_db() as (db, cursor):
    #             # Find user by username
    #             cursor.execute(
    #                 "SELECT id, username, email, hashed_password, is_active FROM users WHERE username = %s",
    #                 (form_data.username,)
    #             )
    #             user_data = cursor.fetchone()

    #             if not user_data:
    #                 raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    #             # Verify password
    #             if not verify_password(form_data.password, user_data['hashed_password']):
    #                 raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    #             if not user_data['is_active']:
    #                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    #             # Create and return token
    #             access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    #             access_token = create_access_token(
    #                 data={"sub": user_data['username']}, expires_delta=access_token_expires
    #             )
    #             return {"access_token": access_token, "token_type": "bearer"}

    #     except mysql.connector.Error as e:
    #         print(f"DB Error during login for user {form_data.username}: {e}")
    #         raise HTTPException(status_code=500, detail="Login failed due to database error.")
    #     except HTTPException as e:
    #         raise e # Re-raise auth related exceptions
    #     except Exception as e:
    #         print(f"Unexpected error during login for user {form_data.username}: {e}")
    #         raise HTTPException(status_code=500, detail="An unexpected error occurred during login.")


    # @app.post("/users/signup", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
    # async def create_user(user: UserCreate):
    #     """Registers a new user."""
    #     hashed_password = get_password_hash(user.password)
    #     try:
    #         with get_db() as (db, cursor):
    #             # Check if user or email already exists
    #             cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (user.username, user.email))
    #             if cursor.fetchone():
    #                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already registered")

    #             # Insert new user
    #             cursor.execute(
    #                 "INSERT INTO users (username, email, hashed_password) VALUES (%s, %s, %s)",
    #                 (user.username, user.email, hashed_password)
    #             )
    #             user_id = cursor.lastrowid
    #             if not user_id:
    #                 raise Exception("Failed to get ID for new user.")

    #             # Fetch the created user details (excluding password) to return
    #             cursor.execute("SELECT id, username, email, is_active FROM users WHERE id = %s", (user_id,))
    #             new_user_data = cursor.fetchone()

    #             return UserInDB(**new_user_data) # Return created user info

    #     except mysql.connector.Error as e:
    #         print(f"DB Error during signup for user {user.username}: {e}")
    #         # Check for duplicate entry error specifically if needed (err.errno == 1062)
    #         if e.errno == 1062: # Duplicate entry
    #             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already registered.")
    #         raise HTTPException(status_code=500, detail="User registration failed due to database error.")
    #     except HTTPException as e:
    #         raise e
    #     except Exception as e:
    #         print(f"Unexpected error during signup for user {user.username}: {e}")
    #         raise HTTPException(status_code=500, detail="An unexpected error occurred during signup.")

    # # Example of getting current user (add to relevant endpoints)
    # @app.get("/users/me", response_model=UserInDB)
    # async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    #     """Returns the details of the currently authenticated user."""
    #     return current_user