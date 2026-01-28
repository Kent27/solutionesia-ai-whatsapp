from pydantic import BaseModel

# Organization Permission Models
class OrganizationCheckPermissionRequest(BaseModel):
    org_id: str
    permission: str

    class Config:
        from_attributes = True