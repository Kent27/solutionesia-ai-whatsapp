from app.models.organization_models import OrganizationUpdateUserPhoneNumber
from app.services.auth_service import AuthService
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from typing import List
from ..models.organization_models import (
    OrganizationCreate, OrganizationResponse, OrganizationLogin, 
    Token, OrganizationUpdateStatus, OrganizationUpdateProfile,
    Token, OrganizationUpdateStatus, OrganizationUpdateProfile,
    OrganizationUserInvite, OrganizationUserUpdate, OrganizationUserResponse,
    OrganizationUserInvite, OrganizationUserUpdate, OrganizationUserResponse,
    OrganizationContactsListResponse, OrganizationsListResponse, ContactsListResponse,
    ConversationFilter
)
from ..models.conversation_models import ConversationsListResponse
from ..services.organization_service import OrganizationService
from ..utils.auth_utils import get_current_admin_user, get_current_user
from typing import Dict, Any
import logging
import jwt as pyjwt
import os
from fastapi import Query
from fastapi import Query

router = APIRouter(prefix="/api/organizations", tags=["Organization"])
logger = logging.getLogger(__name__)

org_service = OrganizationService()
auth_service = AuthService()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="organization/login")

@router.get("", response_model=OrganizationsListResponse)
async def list_organizations(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    List all organizations.
    Allowed for: App Admin.
    """
    try:
        return await org_service.get_all_organizations(page, limit)
    except Exception as e:
        logger.error(f"Error listing organizations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/register", response_model=Dict[str, Any])
async def register_organization(
    org_data: OrganizationCreate,
    _: dict = Depends(get_current_admin_user)
):
    try:
        org = await org_service.create_organization(org_data)
        if not org:
            raise HTTPException(status_code=400, detail="Organization could not be created")

        # Create user if user is not exist
        if org_data.password and org_data.email:
            user = await auth_service.get_user_by_email(org_data.email)
            if not user:
                user = await auth_service.create_user(
                    name=org_data.name,
                    email=org_data.email,
                    password=org_data.password
                )

            admin_id = await auth_service.get_role_id("admin")
            if not admin_id:
                raise HTTPException(status_code=400, detail="Admin role not found")

            org_user = await org_service.invite_user(str(org['id']), user['email'], str(admin_id))

            return { "org": org, "user": user, "org_user": org_user }

        return { "org": org }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"detail": str(e), "trace": traceback.format_exc()})

@router.put("/{org_id}/status", response_model=OrganizationResponse)
async def update_organization_status(
    org_id: str, 
    status_data: OrganizationUpdateStatus,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Update organization status.
    Allowed for: App Admin.
    """
    org = await org_service.update_status(org_id, status_data)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.get("/{org_id}/users", response_model=List[OrganizationUserResponse])
async def get_organization_users(
    org_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all users in an organization.
    Allowed for: App Admin or Member of the organization.
    """
    try:
        user_id = current_user["id"]
        
        # Check permissions
        is_member = await org_service.check_is_org_member(org_id, user_id)
        
        if is_member:
             return await org_service.get_organization_users(org_id)

        # Helper to check app admin if not member
        if await CheckIsAppAdmin(user_id):
            return await org_service.get_organization_users(org_id)
            
        raise HTTPException(status_code=403, detail="Not authorized to view organization users")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting org users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    except Exception as e:
        logger.error(f"Error getting org users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{org_id}/contacts", response_model=ContactsListResponse)
async def get_organization_contacts(
    org_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get organization contacts.
    Allowed for: App Admin or Member of the organization.
    """
    try:
        user_id = current_user["id"]
        
        # Check permissions
        is_member = await org_service.check_is_org_member(org_id, user_id)
        is_admin = await CheckIsAppAdmin(user_id)
        
        if not (is_member or is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to view organization contacts")

        return await org_service.get_organization_contacts(org_id, page, limit)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting org contacts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{org_id}/contacts/{contact_id}/conversations", response_model=ConversationsListResponse)
async def get_contact_conversations(
    org_id: str,
    contact_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get conversations for a specific contact.
    Allowed for: App Admin or Member of the organization.
    """
    try:
        user_id = current_user["id"]
        
        # Check permissions
        is_member = await org_service.check_is_org_member(org_id, user_id)
        is_admin = await CheckIsAppAdmin(user_id)
        
        if not (is_member or is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to view contact conversations")

        conversations = await org_service.get_contact_conversations(org_id, contact_id, page, limit)
        if conversations is None:
             raise HTTPException(status_code=404, detail="Contact not found in organization")
             
        return conversations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contact conversations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{org_id}/conversations/human", response_model=ConversationsListResponse)
async def get_organization_human_conversations(
    org_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get organization conversations with mode 'human'.
    Allowed for: App Admin or Member.
    """
    try:
        user_id = current_user["id"]
        
        # Check permissions
        is_member = await org_service.check_is_org_member(org_id, user_id)
        is_admin = await CheckIsAppAdmin(user_id)
        
        if not (is_member or is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to view organization conversations")

        return await org_service.get_organization_human_conversations(org_id, page, limit)
    except Exception as e:
        logger.error(f"Error getting human conversations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{org_id}/conversations", response_model=ConversationsListResponse)
async def get_organization_conversations(
    org_id: str,
    filter: ConversationFilter,
    current_user: dict = Depends(get_current_user)
):
    """
    Get organization conversations with optional filters (mode, status).
    Allowed for: App Admin or Organization Member.
    """
    try:
        user_id = current_user["id"]
        
        # Check permissions
        is_member = await org_service.check_is_org_member(org_id, user_id)
        is_admin = await CheckIsAppAdmin(user_id)
        
        if not (is_member or is_admin):
            raise HTTPException(status_code=403, detail="Not authorized to view organization conversations")

        return await org_service.get_organization_conversations(org_id, filter)
    except Exception as e:
        logger.error(f"Error searching org conversations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{org_id}/users/invite", response_model=OrganizationUserResponse)
async def invite_user_to_organization(
    org_id: str,
    invite_data: OrganizationUserInvite,
    current_user: dict = Depends(get_current_user)
):
    """
    Invite a user to the organization.
    Allowed for: Organization Admin.
    """
    try:
        user_id = current_user["id"]
        if not await org_service.check_is_org_admin(org_id, user_id):
            raise HTTPException(status_code=403, detail="Only organization admins can invite users")
            
        result = await org_service.invite_user(org_id, invite_data.email)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error inviting user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{org_id}/users/{target_user_id}/role", response_model=OrganizationUserResponse)
async def update_organization_user_role(
    org_id: str,
    target_user_id: str,
    update_data: OrganizationUserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a user's role in the organization.
    Allowed for: Organization Admin.
    """
    try:
        user_id = current_user["id"]
        if not await org_service.check_is_org_admin(org_id, user_id):
            raise HTTPException(status_code=403, detail="Only organization admins can update roles")
            
        result = await org_service.update_user_role(org_id, target_user_id, update_data.role_id)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating org user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{org_id}/users/{target_user_id}/phone-number", response_model=OrganizationUserResponse)
async def update_organization_user_phone_number(
    org_id: str,
    data: OrganizationUpdateUserPhoneNumber,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a user's phone number in the organization.
    Allowed for: Organization User.
    """
    try:
        user_id = current_user["id"]

        result = await org_service.update_user_phone_number(
            org_id,
            user_id,
            data.phone_number
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating org user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{org_id}/users/{target_user_id}")
async def remove_user_from_organization(
    org_id: str,
    target_user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove user from the organization.
    Allowed for: Organization Admin.
    """
    try:
        user_id = current_user["id"]
        if not await org_service.check_is_org_admin(org_id, user_id):
            raise HTTPException(status_code=403, detail="Only organization admins can invite users")

        success = await org_service.remove_user(org_id, target_user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found in organization")
        return {"message": "User removed from organization"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing org user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

async def CheckIsAppAdmin(user_id: str) -> bool:
     try:
          query = "SELECT r.name FROM users u JOIN roles r ON u.role_id = r.id WHERE u.id = %s"
          res = await org_service.db.fetch_one(query, (user_id,))
          if res and res[0] == 'admin':
               return True
          return False
     except:
          return False

