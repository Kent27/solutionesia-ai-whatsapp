from app.services.auth_service import check_is_app_admin
from app.models.organization_models import OrganizationUserUpdate
from app.models.organization_models import OrganizationUserInvite
from app.models.organization_models import RegisterOrganizationResponse
from typing import Optional
from app.models.organization_permission_models import (
    OrganizationCheckPermissionRequest,
    OrganizationPermissionCreate,
    OrganizationPermissionResponse,
    OrganizationRoleCreate,
    OrganizationRoleResponse,
    OrganizationRoleUpdate,
    AssignPermissionRequest,
    CheckPermissionRequest,
)
from app.models.organization_models import OrganizationUpdateUserPhoneNumber
from app.services.auth_service import AuthService
from app.services.organization_permission_service import OrganizationPermissionService
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from typing import List, Dict, Any
from ..models.organization_models import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdateStatus,
    OrganizationsListResponse,
    ConversationFilter,
    GetOrganizationUsersResponse,
    OrganizationListFilter,
)
from ..models.conversation_models import ConversationsListResponse
from ..services.organization_service import OrganizationService
from ..utils.auth_utils import get_current_admin_user, get_current_user
import logging

router = APIRouter(prefix="/api/organizations", tags=["Organization"])
logger = logging.getLogger(__name__)

org_service = OrganizationService()
auth_service = AuthService()
org_perm_service = OrganizationPermissionService()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="organization/login")


@router.post("/check-permission", response_model=Dict[str, Any])
async def check_permission(
    data: OrganizationCheckPermissionRequest,
    current_user: dict = Depends(get_current_user),
):
    access = await org_service.check_org_permission(
        data.org_id, current_user["id"], data.permission
    )
    return {"has_permission": str(access)}


@router.get("", response_model=OrganizationsListResponse)
async def list_organizations(
    filter: OrganizationListFilter = Depends(),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    List all organizations with filters.
    Allowed for: App Admin.
    """
    try:
        return await org_service.get_all_organizations(filter)
    except Exception as e:
        logger.error(f"Error listing organizations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/register", response_model=RegisterOrganizationResponse)
async def register_organization(
    org_data: OrganizationCreate, _: dict = Depends(get_current_admin_user)
):
    try:
        # Create organization
        org = await org_service.create_organization(org_data)
        if not org:
            raise HTTPException(
                status_code=400, detail="Organization could not be created"
            )

        # Create default user if password provided
        if org_data.password and org_data.email:
            user = await auth_service.get_user_by_email(org_data.email)
            if not user:
                user = await auth_service.create_user(
                    name=org_data.name, email=org_data.email, password=org_data.password
                )

            admin_id = await auth_service.get_role_id("admin")
            if not admin_id:
                raise HTTPException(status_code=400, detail="Admin role not found")

        # Init org roles: 'admin' and 'user'
        await org_perm_service.init_org_roles(str(org.id))

        if org_data.password and org_data.email:
            user = await auth_service.get_user_by_email(org_data.email)
            if not user:
                user = await auth_service.create_user(
                    name=org_data.name, email=org_data.email, password=org_data.password
                )

            admin_id = await auth_service.get_role_id("admin")
            if not admin_id:
                raise HTTPException(status_code=400, detail="Admin role not found")

            org_user = await org_service.invite_user(str(org.id), user['email'])

            # Update default user to 'admin' role
            roles = await org_perm_service.get_org_roles(str(org.id))
            admin_role = next((r for r in roles if r["name"] == "admin"), None)

            if admin_role and org_user:
                await org_service.update_user_role(
                    str(org.id),
                    str(user['id']),
                    organization_role_id=str(admin_role["id"]),
                )
                org_user = await org_service.get_organization_user(
                    str(org.id), str(user['id'])
                )

            return RegisterOrganizationResponse(org=org, user=user, org_user=org_user)

        return RegisterOrganizationResponse(org=org)
    except ValueError as e:
        import traceback

        return JSONResponse(
            status_code=500, content={"detail": str(e), "trace": traceback.format_exc()}
        )
    except Exception as e:
        import traceback

        return JSONResponse(
            status_code=500, content={"detail": str(e), "trace": traceback.format_exc()}
        )


@router.put("/{org_id}/status", response_model=OrganizationResponse)
async def update_organization_status(
    org_id: str,
    status_data: OrganizationUpdateStatus,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Update organization status.
    Allowed for: App Admin.
    """
    org = await org_service.update_status(org_id, status_data)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("/{org_id}/users", response_model=List[GetOrganizationUsersResponse])
async def get_organization_users(
    org_id: str, current_user: dict = Depends(get_current_user)
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
        if await check_is_app_admin(user_id):
            return await org_service.get_organization_users(org_id)

        raise HTTPException(
            status_code=403, detail="Not authorized to view organization users"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting org users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    except Exception as e:
        logger.error(f"Error getting org users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{org_id}/contacts", response_model=Dict[str, Any])
async def get_organization_contacts(
    org_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    Get organization contacts.
    Allowed for: App Admin or Member of the organization.
    """
    try:
        user_id = current_user["id"]

        # Check permissions
        is_member = await org_service.check_is_org_member(org_id, user_id)
        is_admin = await check_is_app_admin(user_id)

        if not (is_member or is_admin):
            raise HTTPException(
                status_code=403, detail="Not authorized to view organization contacts"
            )

        return await org_service.get_organization_contacts(org_id, page, limit)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting org contacts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{org_id}/contacts/{contact_id}/conversations",
    response_model=ConversationsListResponse,
)
async def get_contact_conversations(
    org_id: str,
    contact_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    mode: str | None = Query(None, pattern="^(human|ai)$"),
    status: str | None = Query(None, pattern="^(active|inactive)$"),
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get conversations for a specific contact.
    Allowed for: App Admin or Member of the organization.
    """
    try:
        user_id = current_user["id"]

        # Check permissions
        is_member = await org_service.check_is_org_member(org_id, user_id)
        is_admin = await check_is_app_admin(user_id)

        if not (is_member or is_admin):
            raise HTTPException(
                status_code=403, detail="Not authorized to view contact conversations"
            )

        conversations = await org_service.get_contact_conversations(
            org_id,
            contact_id,
            page,
            limit,
            mode=mode,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )
        if conversations is None:
            raise HTTPException(
                status_code=404, detail="Contact not found in organization"
            )

        return conversations

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contact conversations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{org_id}/conversations/new", response_model=ConversationsListResponse)
async def get_organization_new_conversations(
    org_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get new conversation, mode 'human' and is_opened 'False'.
    Allowed for: App Admin or Member.
    """
    try:
        user_id = current_user["id"]

        # Check permissions
        is_member = await org_service.check_is_org_member(org_id, user_id)
        is_admin = await check_is_app_admin(user_id)

        if not (is_member or is_admin):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view organization conversations",
            )

        return await org_service.get_organization_new_conversations(org_id)
    except Exception as e:
        logger.error(f"Error getting human conversations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{org_id}/conversations/new/counts", response_model=Dict[str, Any])
async def get_organization_new_conversations_counts(
    org_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get new conversation, mode 'human' and is_opened 'False'.
    Allowed for: App Admin or Member.
    """
    try:
        user_id = current_user["id"]

        # Check permissions
        is_member = await org_service.check_is_org_member(org_id, user_id)
        is_admin = await check_is_app_admin(user_id)

        if not (is_member or is_admin):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view organization conversations",
            )

        return await org_service.get_organization_new_conversations_counts(org_id)
    except Exception as e:
        logger.error(f"Error getting human conversations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{org_id}/conversations", response_model=ConversationsListResponse)
async def get_organization_conversations(
    org_id: str,
    filter: ConversationFilter,
    current_user: dict = Depends(get_current_user),
):
    """
    Get organization conversations with optional filters (mode, status).
    Allowed for: App Admin or Organization Member.
    """
    try:
        user_id = current_user["id"]

        # Check permissions
        is_member = await org_service.check_is_org_member(org_id, user_id)
        is_admin = await check_is_app_admin(user_id)

        if not (is_member or is_admin):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view organization conversations",
            )

        return await org_service.get_organization_conversations(org_id, filter)
    except Exception as e:
        logger.error(f"Error searching org conversations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{org_id}/users/invite", response_model=GetOrganizationUsersResponse)
async def invite_user_to_organization(
    org_id: str,
    invite_data: OrganizationUserInvite,
    current_user: dict = Depends(get_current_user),
):
    """
    Invite a user to the organization.
    Allowed for: Organization Admin or App admin.
    """
    try:
        user_id = current_user["id"]

        is_org_admin = await org_service.check_is_org_admin(org_id, user_id)
        is_app_admin = await check_is_app_admin(user_id)

        if not (is_org_admin or is_app_admin):
            raise HTTPException(
                status_code=403, detail="Not authorized to invite users"
            )

        result = await org_service.invite_user(org_id, invite_data.email)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error inviting user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/{org_id}/users/{target_user_id}/role", response_model=Optional[GetOrganizationUsersResponse]
)
async def update_organization_user_role(
    org_id: str,
    target_user_id: str,
    update_data: OrganizationUserUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    Update a user's role in the organization.
    Allowed for: Organization Admin.
    """
    try:
        if not await org_service.check_is_org_admin(org_id, current_user["id"]):
            raise HTTPException(
                status_code=403, detail="Not authorized to update user role"
            )

        result = await org_service.update_user_role(
            org_id, target_user_id, organization_role_id=update_data.role_id
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating org user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/{org_id}/users/{target_user_id}/phone-number",
    response_model=Optional[GetOrganizationUsersResponse],
)
async def update_organization_user_phone_number(
    org_id: str,
    target_user_id: str,
    data: OrganizationUpdateUserPhoneNumber,
    _: dict = Depends(get_current_user),
):
    """
    Update a user's phone number in the organization.
    Allowed for: Organization Admin.
    """
    try:
        logger.info(f"Updateing {target_user_id}")
        result = await org_service.update_user_phone_number(
            org_id, target_user_id, data.phone_number
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating org user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{org_id}/users/{target_user_id}")
async def remove_user_from_organization(
    org_id: str, target_user_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Remove user from the organization.
    Allowed for: Organization Admin.
    """
    try:
        user_id = current_user["id"]
        if not await org_service.check_is_org_admin(org_id, user_id):
            raise HTTPException(
                status_code=403, detail="Only organization admins can invite users"
            )

        success = await org_service.remove_user(org_id, target_user_id)
        if not success:
            raise HTTPException(
                status_code=404, detail="User not found in organization"
            )
        return {"message": "User removed from organization"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing org user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# --- RBAC Endpoints ---


# 1. Permissions (App Admin)
@router.post("/permissions", response_model=OrganizationPermissionResponse)
async def create_permission(
    permission: OrganizationPermissionCreate,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Create a new global organization permission.
    Allowed for: App Admin.
    """
    try:
        return await org_perm_service.create_permission(
            permission.name, permission.description
        )
    except Exception as e:
        logger.error(f"Error creating permission: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/permissions", response_model=List[OrganizationPermissionResponse])
async def list_permissions(current_user: dict = Depends(get_current_user)):
    """
    List all permissions.
    Allowed for: All Users.
    """
    try:
        return await org_perm_service.get_permissions()
    except Exception as e:
        logger.error(f"Error listing permissions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/permissions/{perm_id}")
async def delete_permission(
    perm_id: str, current_user: dict = Depends(get_current_admin_user)
):
    """
    Delete a permission.
    Allowed for: App Admin.
    """
    try:
        await org_perm_service.delete_permission(perm_id)
        return {"message": "Permission deleted"}
    except Exception as e:
        logger.error(f"Error deleting permission: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# 2. Roles (Org Admin)
@router.get("/{org_id}/roles", response_model=List[OrganizationRoleResponse])
async def get_org_roles(org_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get all roles in an organization.
    Allowed for: Org Admin.
    """
    try:
        user_id = current_user["id"]
        if not await org_service.check_is_org_admin(org_id, user_id):
            raise HTTPException(status_code=403, detail="Not authorized")

        return await org_perm_service.get_org_roles(org_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting roles: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{org_id}/roles", response_model=OrganizationRoleResponse)
async def create_org_role(
    org_id: str,
    role: OrganizationRoleCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new role for organization.
    Allowed for: Org Admin.
    """
    try:
        user_id = current_user["id"]
        if not await org_service.check_is_org_admin(org_id, user_id):
            raise HTTPException(status_code=403, detail="Not authorized")

        return await org_perm_service.create_org_role(org_id, role.name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating role: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{org_id}/roles/{role_id}", response_model=OrganizationRoleUpdate)
async def update_org_role(
    org_id: str,
    role_id: str,
    role: OrganizationRoleUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update role name"""
    try:
        user_id = current_user["id"]
        if not await org_service.check_is_org_admin(org_id, user_id):
            raise HTTPException(status_code=403, detail="Not authorized")

        return await org_perm_service.update_org_role(role_id, role.name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating role: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{org_id}/roles/{role_id}")
async def delete_org_role(
    org_id: str, role_id: str, current_user: dict = Depends(get_current_user)
):
    """Delete a role"""
    try:
        user_id = current_user["id"]
        if not await org_service.check_is_org_admin(org_id, user_id):
            raise HTTPException(status_code=403, detail="Not authorized")

        await org_perm_service.delete_org_role(org_id, role_id)
        return {"message": "Role deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting role: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{org_id}/roles/{role_id}/permissions")
async def assign_permission_to_role(
    org_id: str,
    role_id: str,
    data: AssignPermissionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Assign permission to role"""
    try:
        user_id = current_user["id"]
        if not await org_service.check_is_org_admin(org_id, user_id):
            raise HTTPException(status_code=403, detail="Not authorized")

        await org_perm_service.assign_permission_to_role(
            org_id, role_id, data.permission_id
        )
        return {"message": "Permission assigned"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning permission: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{org_id}/roles/{role_id}/permissions/{perm_id}")
async def remove_permission_from_role(
    org_id: str,
    role_id: str,
    perm_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove permission from role"""
    try:
        user_id = current_user["id"]
        if not await org_service.check_is_org_admin(org_id, user_id):
            raise HTTPException(status_code=403, detail="Not authorized")

        await org_perm_service.remove_permission_from_role(org_id, role_id, perm_id)
        return {"message": "Permission removed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing permission: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{org_id}/permissions/check")
async def check_organization_permission(
    org_id: str,
    check_request: CheckPermissionRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Check if user has specific permission in organization.
    Allowed for: Organization Member.
    """
    try:
        user_id = current_user["id"]
        # Basic membership check first
        if not await org_service.check_is_org_member(org_id, user_id):
            # If not a member, check if app admin
            if not await check_is_app_admin(user_id):
                raise HTTPException(
                    status_code=403, detail="Not a member of organization"
                )

        has_permission = await org_service.check_org_permission(
            org_id, user_id, check_request.permission
        )
        return {"has_permission": has_permission}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking permission: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{org_id}/roles/me", response_model=Dict[str, str])
async def get_organization_user_role(
    org_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get role for the current user in the organization.
    Allowed for: Organization Member.
    """
    try:
        user_id = current_user["id"]
        # Basic membership check first
        if not await org_service.check_is_org_member(org_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of organization")

        role = await org_service.get_org_user_role(org_id, user_id)
        return {"role": role}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user role: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{org_id}/permissions/me", response_model=List[str])
async def get_organization_user_permissions(
    org_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get all permissions for the current user in the organization.
    Allowed for: Organization Member.
    """
    try:
        user_id = current_user["id"]
        # Basic membership check first
        if not await org_service.check_is_org_member(org_id, user_id):
            # If not a member, check if app admin
            if not await check_is_app_admin(user_id):
                raise HTTPException(
                    status_code=403, detail="Not a member of organization"
                )

        permissions = await org_service.get_org_user_permissions(org_id, user_id)
        return permissions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user permissions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
