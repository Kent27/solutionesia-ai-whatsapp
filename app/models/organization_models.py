from app.models.auth_models import UserResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re
from .contact_models import ContactResponse, ContactsListResponse
from .conversation_models import ConversationResponse


# Organization Models
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    phone_id: str | None = Field(None, min_length=1)
    agent_id: str | None = Field(None, min_length=1)

    @validator("email")
    def validate_email(cls, v):
        if v and not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Email must be a valid email address")
        return v


class OrganizationCreate(OrganizationBase):
    password: str | None = Field(None, min_length=8)
    phone_number: str | None = Field(None, min_length=8)


class OrganizationUpdateStatus(BaseModel):
    status: str

    @validator("status")
    def validate_status(cls, v):
        if v not in ["active", "inactive", "pending"]:
            raise ValueError("Status must be active, inactive, or pending")
        return v


class OrganizationUpdateProfile(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    password: Optional[str] = Field(None, min_length=6)


class OrganizationLogin(BaseModel):
    email: str
    password: str


class GetOrganizationResponse(OrganizationBase):
    id: str
    agent_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None


class OrganizationResponse(OrganizationBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationsListResponse(BaseModel):
    organizations: List[OrganizationResponse]
    total: int
    page: int
    limit: int


class OrganizationContactWithConversationsResponse(ContactResponse):
    conversations: List[ConversationResponse]


class OrganizationContactsListResponse(BaseModel):
    items: List[OrganizationContactWithConversationsResponse]
    total: int
    page: int
    limit: int
    pages: int


# Role Models
class RoleBase(BaseModel):
    name: str = Field(..., min_length=1)
    color: str = Field(default="#000000")

    @validator("color")
    def validate_color(cls, v):
        # Validate hex color format
        if v and not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", v):
            raise ValueError("Color must be a valid hex color code (e.g., #000000)")
        return v


class RoleCreate(RoleBase):
    pass


class RoleResponse(RoleBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Organization User Models
class OrganizationUserBase(BaseModel):
    user_id: str
    organization_id: str
    role_id: str


class OrganizationUserCreate(OrganizationUserBase):
    pass


class OrganizationUserInvite(BaseModel):
    email: str


class OrganizationUserUpdate(BaseModel):
    role_id: str


class OrganizationUserResponse(BaseModel):
    id: str
    user: dict  # Contains user info like name, email
    role: dict  # Contains role info like name
    phone_number: str
    organization_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationUpdateUserPhoneNumber(BaseModel):
    phone_number: str


class ConversationFilter(BaseModel):
    mode: Optional[str] = Field(None, pattern="^(human|ai)$")
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")
    query: Optional[str] = None
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    is_opened: Optional[bool] = None
    page: int = 1
    limit: int = 10


# Organization Permission Models
class OrganizationPermissionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=255)

    class Config:
        from_attributes = True


class GetOrganizationUser(BaseModel):
    id: str
    name: str
    profile_picture: Optional[str] = None
    email: str


class GetOrganizationRole(BaseModel):
    id: str
    name: str


class GetOrganizationUsersResponse(BaseModel):
    id: str
    user: GetOrganizationUser
    organization_id: str
    phone_number: Optional[str]
    organization_role: GetOrganizationRole
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RegisterOrganizationResponse(BaseModel):
    org: OrganizationResponse
    user: Optional[UserResponse] = None
    org_user: Optional[GetOrganizationUsersResponse] = None


class OrganizationListFilter(BaseModel):
    query: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")
    page: int = 1
    limit: int = 10
