from app.models.conversation_models import ConversationStatusUpdate
from app.utils.auth_utils import get_current_user
from fastapi import APIRouter, HTTPException, Path, Body, Depends
from ..services.conversation_service import ConversationService
from ..models.conversation_models import ConversationModeUpdate

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
conversation_service = ConversationService()

@router.put("/{conversation_id}/mode", response_model=dict)
async def update_conversation_mode(
    conversation_id: str = Path(..., description="The ID of the conversation to update"),
    mode_update: ConversationModeUpdate = Body(...)
):
    """
    Update the mode of a conversation to either 'human' or 'ai'.
    """
    try:
        success = await conversation_service.update_conversation_mode(conversation_id, mode_update.mode)
        if success:
             return {
                 "status": "success",
                 "message": f"Conversation mode updated to '{mode_update.mode}'",
                 "conversation_id": conversation_id,
                 "mode": mode_update.mode
             }
        else:
             raise HTTPException(status_code=400, detail="Failed to update conversation mode")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{conversation_id}/status", response_model=dict)
async def update_conversation_status(
    conversation_id: str = Path(..., description="The ID of the conversation to update"),
    status_update: ConversationStatusUpdate = Body(...),
):
    """
    Update conversation status to 'active' or 'inactive'
    """
    try:
        success = await conversation_service.update_conversation_status(conversation_id, status_update.status)

        if success:
             return {
                 "status": "success",
                 "message": f"Conversation status updated to '{status_update.status}'",
                 "conversation_id": conversation_id,
                 "status": status_update.status
             }
        else:
             raise HTTPException(status_code=400, detail="Failed to update conversation status")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
