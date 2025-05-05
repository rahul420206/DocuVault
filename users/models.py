# users/models.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    username: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str # Add role field

class UserInDB(UserBase):
    id: int
    role: Optional[str]

    class Config:
        from_attributes = True

class UserInDBInternal(UserInDB):
    password: str

# Although Token models are used by auth, they are closely related to the user login process.
# You could put them here or in auth/models.py if you create that structure.
# For now, let's keep them here.
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None