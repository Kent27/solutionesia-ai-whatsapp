from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re

class ContactBase(BaseModel):
    name: str = Field(..., min_length=1)
    phoneNumber: str = Field(..., min_length=8)
    email: str | None = Field(None)
    stamps: str | None = Field(None)
    organizationId: str | None = Field(None)
    
    @validator('phoneNumber')
    def validate_phone_number(cls, v):
        # Simple validation to ensure phone number starts with + and contains only digits after that
        if not re.match(r'^\+\d+$', v):
            raise ValueError('Phone number must start with + and contain only digits')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Email must be a valid email address')
        return v
    
class ContactCreate(ContactBase):
    labels: List[str] = Field(default_factory=list)

class ContactResponse(ContactBase):
    id: str
    profilePicture: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True

class ContactsListResponse(BaseModel):
    contacts: List[ContactResponse]
    total: int
    page: int
    limit: int

class AddLabelRequest(BaseModel):
    labelId: str = Field(..., min_length=1) 