# documents/models.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Pydantic model for a single document
class Document(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    latest_file_path: Optional[str] = None # This might not be needed in the response model if not directly used by frontend lists
    created_at: datetime

    class Config:
        orm_mode = True # Allows mapping from database rows (dictionaries)

# Pydantic model for a document version
class DocumentVersion(BaseModel):
    id: int
    version: int
    file_path: str # This might not be needed in the response model if not directly used by frontend lists
    uploaded_at: datetime

    class Config:
        orm_mode = True

# Pydantic model for a single search result item
# This model is used by the SearchResults model
class PerQueryResult(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    latest_file_path: Optional[str] = None
    created_at: datetime
    # FIX: Add owner_username to the search result model
    owner_username: Optional[str] = None # Add this field

    class Config:
        orm_mode = True

# Pydantic model for the overall search results response
class SearchResults(BaseModel):
    results: List[PerQueryResult]

