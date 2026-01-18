from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re

class LabelBase(BaseModel):
    name: str = Field(..., min_length=1)
    color: str = Field(default="#25D366")
    
    @validator('color')
    def validate_color(cls, v):
        # Validate hex color format
        if not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', v):
            raise ValueError('Color must be a valid hex color code (e.g., #25D366)')
        return v

class LabelCreate(LabelBase):
    pass

class LabelResponse(LabelBase):
    id: str
    
    class Config:
        from_attributes = True

class LabelsListResponse(BaseModel):
    labels: List[LabelResponse]
    total: int
    page: int
    limit: int 