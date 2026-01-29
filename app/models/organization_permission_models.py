from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# Organization Permission Models
class OrganizationCheckPermissionRequest(BaseModel):
    org_id: str
    permission: str

    class Config:
        from_attributes = True


class CheckPermissionRequest(BaseModel):
    permission: str


class OrganizationPermissionBase(BaseModel):
    name: str
    description: str


class OrganizationPermissionCreate(OrganizationPermissionBase):
    pass


class OrganizationPermissionResponse(OrganizationPermissionBase):
    id: str

    class Config:
        from_attributes = True


class OrganizationRoleBase(BaseModel):
    name: str


class OrganizationRoleCreate(OrganizationRoleBase):
    pass


class OrganizationRoleUpdate(OrganizationRoleBase):
    pass


class OrganizationRoleResponse(OrganizationRoleBase):
    id: str
    organization_id: str
    permissions: List[OrganizationPermissionResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssignPermissionRequest(BaseModel):
    permission_id: str
