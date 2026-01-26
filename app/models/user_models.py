from pydantic import BaseModel
from typing import List, Optional
from pydantic import Field

class UserListFilter(BaseModel):
    role: Optional[str] = Field(None, pattern="^(admin|user)$")
    search: Optional[str] = None
    page: int = 1
    limit: int = 10

class UserRoleResponse(BaseModel):
    id: str
    name: str

class UserOrgRoleResponse(BaseModel):
    id: str
    name: str

class OrganizationUserDetail(BaseModel):
    phone_number: Optional[str]
    role: UserOrgRoleResponse

class UserOrganizationResponse(BaseModel):
    id: str
    name: str
    email: str
    status: str
    organization_user: OrganizationUserDetail

class UserProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str # Global role
    role: str # Global role
    profile_picture: Optional[str] = None

class UsersListResponse(BaseModel):
    users: List[UserProfileResponse]
    total: int
    page: int
    limit: int
