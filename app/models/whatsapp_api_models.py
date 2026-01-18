from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    LOCATION = "location"
    UNKNOWN = "unknown"

class MessageStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    PENDING = "pending"

class WhatsAppDirectMessage(BaseModel):
    id: str
    timestamp: Optional[int] = None
    readable_time: Optional[str] = None
    status: Optional[str] = None
    type: MessageType
    from_: str = Field(..., alias="from")
    to: Optional[str] = None
    direction: MessageDirection
    content: Optional[str] = None
    media_id: Optional[str] = None
    caption: Optional[str] = None
    filename: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    name: Optional[str] = None
    address: Optional[str] = None
    
    class Config:
        populate_by_name = True

class WhatsAppDirectMessagesResponse(BaseModel):
    messages: List[WhatsAppDirectMessage]
    total: int

class WhatsAppContact(BaseModel):
    """Model for WhatsApp contact details"""
    wa_id: str
    profile: Optional[Dict[str, Any]] = None
    name: Optional[str] = None 
    phone_number: Optional[str] = None
    status: Optional[str] = None
    about: Optional[str] = None
    email: Optional[str] = None
    last_active_timestamp: Optional[int] = None
    readable_last_active: Optional[str] = None
    whatsapp_business_account_id: Optional[str] = None

class WhatsAppContactResponse(BaseModel):
    """Response model for WhatsApp contact information"""
    contact: WhatsAppContact
    success: bool
    error_message: Optional[str] = None 