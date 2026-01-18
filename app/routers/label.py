from fastapi import APIRouter, HTTPException, Depends, Query
from ..models.label_models import LabelCreate, LabelResponse, LabelsListResponse
from ..services.label_service import LabelService
from ..utils.auth_utils import get_current_user
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/labels", tags=["labels"])
label_service = LabelService()

@router.get("", response_model=LabelsListResponse)
async def get_labels(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get labels for the authenticated user
    """
    try:
        result = await label_service.get_labels(
            user_id=current_user["id"],
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Error getting labels: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving labels: {str(e)}"
        )

@router.post("", response_model=LabelResponse)
async def create_label(
    label_data: LabelCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new label
    """
    try:
        result = await label_service.create_label(
            user_id=current_user["id"],
            name=label_data.name,
            color=label_data.color
        )
        
        if not result:
            raise HTTPException(
                status_code=400,
                detail="Label with this name already exists"
            )
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating label: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error creating label: {str(e)}"
        ) 