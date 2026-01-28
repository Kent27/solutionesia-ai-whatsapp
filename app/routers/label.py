from fastapi import APIRouter, HTTPException, Depends, Query, Path
from ..models.label_models import LabelCreate, LabelResponse, LabelsListResponse
from ..services.label_service import LabelService
from ..services.organization_service import OrganizationService
from ..utils.auth_utils import get_current_user
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)
# Changed prefix and tags to reflect organization scope
router = APIRouter(
    prefix="/api/organizations/{org_id}/labels", tags=["Organization Labels"]
)
label_service = LabelService()
org_service = OrganizationService()

async def verify_org_access(org_id: str, current_user: Dict[str, Any]):
    """Verify user has access to organization"""
    user_id = current_user["id"]
    is_member = await org_service.check_is_org_member(org_id, user_id)

    # Check if app admin
    # This logic mimics what is in organization.py
    is_admin = False
    try:
        query = "SELECT r.name FROM users u JOIN roles r ON u.role_id = r.id WHERE u.id = %s"
        res = await org_service.db.fetch_one(query, (user_id,))
        if res and res[0] == "admin":
            is_admin = True
    except Exception as e:
        logger.error(f"Error checking user role: {str(e)}", exc_info=True)
        pass

    if not (is_member or is_admin):
        raise HTTPException(
            status_code=403, detail="Not authorized to access organization labels"
        )


@router.get("", response_model=LabelsListResponse)
async def get_labels(
    org_id: str = Path(..., description="Organization ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get labels for an organization
    Allowed for: App Admin or Organization Member
    """
    try:
        await verify_org_access(org_id, current_user)

        result = await label_service.get_labels(
            organization_id=org_id, page=page, limit=limit
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting labels: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving labels: {str(e)}"
        )


@router.post("", response_model=LabelResponse)
async def create_label(
    label_data: LabelCreate,
    org_id: str = Path(..., description="Organization ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Create a new label for an organization
    Allowed for: App Admin or Organization Member
    """
    try:
        await verify_org_access(org_id, current_user)

        result = await label_service.create_label(
            organization_id=org_id, name=label_data.name, color=label_data.color
        )

        if not result:
            raise HTTPException(
                status_code=400,
                detail="Label with this name already exists in the organization",
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating label: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating label: {str(e)}")


@router.put("/{label_id}", response_model=LabelResponse)
async def update_label(
    label_data: LabelCreate,
    org_id: str = Path(..., description="Organization ID"),
    label_id: str = Path(..., description="Label ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Update a label
    Allowed for: App Admin or Organization Member
    """
    try:
        await verify_org_access(org_id, current_user)

        result = await label_service.update_label(
            organization_id=org_id,
            label_id=label_id,
            name=label_data.name,
            color=label_data.color,
        )

        if not result:
            raise HTTPException(status_code=404, detail="Label not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating label: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating label: {str(e)}")


@router.delete("/{label_id}")
async def delete_label(
    org_id: str = Path(..., description="Organization ID"),
    label_id: str = Path(..., description="Label ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Delete a label
    Allowed for: App Admin or Organization Member
    """
    try:
        await verify_org_access(org_id, current_user)

        result = await label_service.delete_label(
            organization_id=org_id, label_id=label_id
        )

        if not result:
            raise HTTPException(status_code=404, detail="Label not found")

        return {"message": "Label deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting label: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting label: {str(e)}")


@router.post("/contacts/{contact_id}/assign/{label_id}")
async def assign_label_to_contact(
    org_id: str = Path(..., description="Organization ID"),
    contact_id: str = Path(..., description="Contact ID"),
    label_id: str = Path(..., description="Label ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Assign a label to a contact
    Allowed for: App Admin or Organization Member
    """
    try:
        await verify_org_access(org_id, current_user)

        await label_service.assign_label(
            organization_id=org_id, contact_id=contact_id, label_id=label_id
        )

        return {"message": "Label assigned successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning label: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error assigning label: {str(e)}")


@router.delete("/contacts/{contact_id}/remove/{label_id}")
async def remove_label_from_contact(
    org_id: str = Path(..., description="Organization ID"),
    contact_id: str = Path(..., description="Contact ID"),
    label_id: str = Path(..., description="Label ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Remove a label from a contact
    Allowed for: App Admin or Organization Member
    """
    try:
        await verify_org_access(org_id, current_user)

        await label_service.remove_label_from_contact(
            organization_id=org_id, contact_id=contact_id, label_id=label_id
        )

        return {"message": "Label removed from contact successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing label: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error removing label: {str(e)}")
