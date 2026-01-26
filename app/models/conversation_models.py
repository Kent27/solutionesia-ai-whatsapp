from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from .contact_models import ContactResponse

# Conversation Models
class ConversationBase(BaseModel):
    name: str
    phoneNumber: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    mode: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)

class ConversationResponse(ConversationBase):
    id: str
    lastMessage: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ConversationsListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
    page: int
    limit: int

class ConversationMessageResponse(BaseModel):
    content: str
    contentType: Optional[str] = None
    role: str
    status: Optional[str] = None
    timestamp: datetime

class ConversationDetailResponse(ConversationResponse):
    contact: Optional[ContactResponse] = None
    messages: List[ConversationMessageResponse] = []

class ConversationModeUpdate(BaseModel):
    mode: str = Field(..., pattern="^(human|ai)$", description="Mode of the conversation: 'human' or 'ai'")

class ConversationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|inactive)$", description="Status of the conversation: 'active' or 'inactive'")

# Message Models
class MessageBase(BaseModel):
    conversation_id: str
    content: str
    content_type: Optional[str] = Field(None)
    role: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class MessagesListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
    page: int
    limit: int

# Memory Unit Models
class MemoryUnitBase(BaseModel):
    conversation_id: str
    abstracted_content: Optional[str] = Field(None)
    embedding_vector: Optional[bytes] = Field(None)
    keywords: Optional[Dict[str, Any]] = Field(None)
    consolidation_level: int = Field(default=0)

class MemoryUnitCreate(MemoryUnitBase):
    pass

class MemoryUnitResponse(MemoryUnitBase):
    id: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

class MemoryUnitsListResponse(BaseModel):
    memory_units: List[MemoryUnitResponse]
    total: int
    page: int
    limit: int
