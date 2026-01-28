from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re


class LabelBase(BaseModel):
    name: str = Field(..., min_length=1)
    color: str = Field(default="#25D366")

    @validator("color")
    def validate_color(cls, v):
        # Validate hex color format
        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", v):
            raise ValueError("Color must be a valid hex color code (e.g., #25D366)")
        return v


class LabelCreate(LabelBase):
    organization_id: Optional[str] = None


class LabelResponse(LabelBase):
    id: str
    organization_id: str

    class Config:
        from_attributes = True


class LabelsListResponse(BaseModel):
    labels: List[LabelResponse]
    total: int
    page: int
    limit: int


class ContactLabelBase(BaseModel):
    contact_id: str
    label_id: str


class ContactLabelCreate(ContactLabelBase):
    pass


class ContactLabelResponse(ContactLabelBase):
    id: str
    created_at: datetime
    label: Optional[LabelResponse] = None

    class Config:
        from_attributes = True
