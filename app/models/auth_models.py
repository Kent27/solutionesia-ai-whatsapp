from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr

class UserLogin(UserBase):
    password: str = Field(..., min_length=8)

class UserRegister(UserBase):
    name: str = Field(..., min_length=2)
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    id: str
    name: str
    profile_picture: Optional[str] = None

    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    user: UserResponse
    token: str 