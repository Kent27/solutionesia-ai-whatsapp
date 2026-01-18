from fastapi import APIRouter, HTTPException, Depends, Query, Path
from ..models.contact_models import ContactCreate, ContactResponse, ContactsListResponse, AddLabelRequest
from ..services.contact_service import ContactService
from ..utils.auth_utils import get_current_user
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/contacts", tags=["contacts"])
contact_service = ContactService()

@router.get("", response_model=ContactsListResponse)
async def get_contacts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get contacts for the authenticated user
    """
    try:
        result = await contact_service.get_contacts(
            user_id=current_user["id"],
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Error getting contacts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving contacts: {str(e)}"
        )

@router.post("", response_model=ContactResponse)
async def create_contact(
    contact_data: ContactCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new contact
    """
    try:
        result = await contact_service.create_contact(
            user_id=current_user["id"],
            name=contact_data.name,
            phone_number=contact_data.phoneNumber,
            labels=contact_data.labels
        )
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to create contact"
            )
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating contact: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error creating contact: {str(e)}"
        )

@router.post("/{contact_id}/labels", response_model=ContactResponse)
async def add_label_to_contact(
    contact_id: str = Path(..., description="Contact ID"),
    label_data: AddLabelRequest = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Add a label to a contact
    """
    try:
        # Check if the contact belongs to the user
        contact = await contact_service.get_contact_by_id(contact_id)
        if not contact:
            raise HTTPException(
                status_code=404,
                detail="Contact not found"
            )
            
        # Add the label to the contact
        success = await contact_service.add_label_to_contact(
            contact_id=contact_id,
            label_id=label_data.labelId
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to add label to contact"
            )
            
        # Get the updated contact
        updated_contact = await contact_service.get_contact_by_id(contact_id)
        if not updated_contact:
            raise HTTPException(
                status_code=404,
                detail="Contact not found after update"
            )
            
        return updated_contact
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding label to contact: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error adding label to contact: {str(e)}"
        ) 