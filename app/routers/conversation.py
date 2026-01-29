from app.services.organization_permission_service import OrganizationPermissionService
from app.services.organization_service import OrganizationService
from app.models.conversation_models import ConversationStatusUpdate
from app.utils.auth_utils import get_current_user
from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Body,
    Depends,
)
from ..services.conversation_service import ConversationService
from ..models.conversation_models import (
    ConversationModeUpdate,
    ConversationDetailResponse,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
conversation_service = ConversationService()
org_service = OrganizationService()
org_permission_service = OrganizationPermissionService()


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_details(
    conversation_id: str = Path(..., description="The ID of the conversation to get"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get conversation details.
    Allowed for: Member of the organization that owns the conversation.
    """
    try:
        user_id = current_user["id"]

        # Check permissions
        has_access = await conversation_service.verify_conversation_access(
            conversation_id, user_id
        )

        if not has_access:
            raise HTTPException(
                status_code=403, detail="Not authorized to view this conversation"
            )
        
        # Set status to opened if permitted user opened the conversation
        can_be_opened = await conversation_service.can_be_opened(conversation_id)
        if can_be_opened:
            can_open = await conversation_service.can_open_conversation(conversation_id, user_id)
            if can_open:
                await conversation_service.update_conversation_open_status(conversation_id, True)

        conversation = await conversation_service.get_conversation_details(
            conversation_id
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{conversation_id}/mode", response_model=dict)
async def update_conversation_mode(
    conversation_id: str = Path(
        ..., description="The ID of the conversation to update"
    ),
    mode_update: ConversationModeUpdate = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Update the mode of a conversation to either 'human' or 'ai'.
    Allowed for: App Admin or Organization Member.
    """
    try:
        user_id = current_user["id"]

        if not await conversation_service.verify_conversation_access(
            conversation_id, user_id
        ):
            raise HTTPException(
                status_code=403, detail="Not authorized to update this conversation"
            )

        success = await conversation_service.update_conversation_mode(
            conversation_id, mode_update.mode
        )
        if success:
            return {
                "status": "success",
                "message": f"Conversation mode updated to '{mode_update.mode}'",
                "conversation_id": conversation_id,
                "mode": mode_update.mode,
            }
        else:
            raise HTTPException(
                status_code=400, detail="Failed to update conversation mode"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{conversation_id}/status", response_model=dict)
async def update_conversation_status(
    conversation_id: str = Path(
        ..., description="The ID of the conversation to update"
    ),
    status_update: ConversationStatusUpdate = Body(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Update conversation status to 'active' or 'inactive'
    Allowed for: App Admin or Organization Member.
    """
    try:
        user_id = current_user["id"]
        if not await conversation_service.verify_conversation_access(
            conversation_id, user_id
        ):
            raise HTTPException(
                status_code=403, detail="Not authorized to update this conversation"
            )

        success = await conversation_service.update_conversation_status(
            conversation_id, status_update.status
        )

        if success:
            return {
                "status": "success",
                "message": f"Conversation status updated to '{status_update.status}'",
                "conversation_id": conversation_id,
                "status": status_update.status,
            }
        else:
            raise HTTPException(
                status_code=400, detail="Failed to update conversation status"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
