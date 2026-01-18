from fastapi import APIRouter, HTTPException, Depends, Query, Path
from ..services.whatsapp_api_service import WhatsAppAPIService
from ..models.whatsapp_api_models import WhatsAppDirectMessagesResponse, WhatsAppDirectMessage, WhatsAppContactResponse, WhatsAppContact
from ..utils.auth_utils import get_current_user
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])
whatsapp_api_service = WhatsAppAPIService()

@router.get("/contact/{phone_number}", response_model=WhatsAppContactResponse)
async def get_whatsapp_contact(
    phone_number: str = Path(..., description="Phone number with or without country code"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get WhatsApp contact information directly from the WhatsApp API for a specific phone number.
    This endpoint uses WhatsApp API 4.0 to retrieve contact details.
    
    Args:
        phone_number: Phone number to get contact info for (with or without country code)
        current_user: Current authenticated user
        
    Returns:
        WhatsApp contact information with metadata
    """
    try:
        # Fetch contact info from WhatsApp API
        contact_result = await whatsapp_api_service.get_contact_info(phone_number=phone_number)
        
        # Check if API call was successful
        if not contact_result.get("success", False):
            raise HTTPException(
                status_code=404,
                detail=contact_result.get("error_message", "Contact not found")
            )
        
        # Return formatted response
        return contact_result
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching WhatsApp contact: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching WhatsApp contact: {str(e)}"
        )

@router.get("/messages/{phone_number}", response_model=WhatsAppDirectMessagesResponse)
async def get_whatsapp_messages(
    phone_number: str = Path(..., description="Phone number with or without country code"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of messages to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get WhatsApp messages directly from the WhatsApp API for a specific phone number.
    This endpoint bypasses the database and fetches real-time data from WhatsApp.
    
    Args:
        phone_number: Phone number to get messages for (with or without country code)
        limit: Maximum number of messages to retrieve
        current_user: Current authenticated user
        
    Returns:
        List of WhatsApp messages with metadata
    """
    try:
        # Fetch messages from WhatsApp API
        messages = await whatsapp_api_service.get_conversation_history(
            phone_number=phone_number,
            limit=limit
        )
        
        if not messages:
            # Return empty response if no messages found
            return {
                "messages": [],
                "total": 0
            }
        
        # Return formatted response
        return {
            "messages": messages,
            "total": len(messages)
        }
    except Exception as e:
        logger.error(f"Error fetching WhatsApp messages: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching WhatsApp messages: {str(e)}"
        ) 