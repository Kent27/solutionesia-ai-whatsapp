from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class RecipientType(str, Enum):
    CONTACT = "contact"
    LABEL = "label"

class MessageStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

class MessageBase(BaseModel):
    content: str = Field(..., min_length=1)
    
class MessageCreate(MessageBase):
    recipientId: str = Field(..., min_length=1)
    recipientType: RecipientType = Field(default=RecipientType.CONTACT)

class MessageResponse(MessageBase):
    id: str
    timestamp: datetime
    status: MessageStatus
    recipientId: str
    recipientType: RecipientType
    
    class Config:
        from_attributes = True

class MessagesListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
    page: int
    limit: int 