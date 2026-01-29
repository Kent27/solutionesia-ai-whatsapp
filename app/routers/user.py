from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging
from ..utils.auth_utils import get_current_user, get_current_admin_user
from ..services.auth_service import AuthService
from ..services.organization_service import OrganizationService
from ..models.user_models import (
    UserProfileResponse,
    UserOrganizationResponse,
    UserListFilter,
    UsersListResponse,
)

router = APIRouter(prefix="/api/users", tags=["users"])
logger = logging.getLogger(__name__)

auth_service = AuthService()
org_service = OrganizationService()


@router.get("/", response_model=UsersListResponse)
async def list_users(
    filter: UserListFilter = Depends(),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    List users with optional filters.
    Allowed for: App Admin only.
    """
    try:
        result = await auth_service.get_all_users(filter)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Get current user profile with global role.
    """
    try:
        user_id = current_user["id"]
        result = await auth_service.get_user_with_role(user_id)
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}/organizations", response_model=List[UserOrganizationResponse])
async def get_user_organizations(
    user_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get organizations specific user belongs to.
    Allowed for: The User or App Admins.
    """
    try:
        if current_user["id"] != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view other user's organizations",
            )

        result = await org_service.get_user_organizations(user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user organizations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=UsersListResponse)
async def search_users(
    filter: UserListFilter, current_user: dict = Depends(get_current_admin_user)
):
    """
    Search and list users with filters.
    Allowed for: App Admin only.
    """
    try:
        return await auth_service.get_all_users(filter)
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
