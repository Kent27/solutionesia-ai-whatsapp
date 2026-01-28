from fastapi import APIRouter, HTTPException, Depends, Query
from ..models.message_models import MessageCreate, MessageResponse, MessagesListResponse
from ..services.message_service import MessageService
from ..services.conversation_service import ConversationService
from ..utils.auth_utils import get_current_user
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/messages", tags=["messages"])
message_service = MessageService()
conversation_service = ConversationService()

# @router.get("", response_model=MessagesListResponse)
# async def get_messages(
#     page: int = Query(1, ge=1, description="Page number"),
#     limit: int = Query(50, ge=1, le=100, description="Items per page"),
#     current_user: Dict[str, Any] = Depends(get_current_user)
# ) -> Dict[str, Any]:
#     """
#     Get messages for the authenticated user
#     """
#     try:
#         result = await message_service.get_messages(
#             user_id=current_user["id"],
#             page=page,
#             limit=limit
#         )
#         return result
#     except Exception as e:
#         logger.error(f"Error getting messages: {str(e)}", exc_info=True)
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error retrieving messages: {str(e)}"
#         )

@router.post("", response_model=MessageResponse)
async def create_message(
    message_data: MessageCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new message
    """
    try:
        user_id = current_user["id"]
        
        # Verify access to conversation
        conversation_id = message_data.conversation_id
        
        if not await conversation_service.verify_conversation_access(conversation_id, user_id):
             raise HTTPException(status_code=403, detail="Not authorized to send message to this conversation")

        result = await message_service.create_message(
            conversation_id=conversation_id,
            content=message_data.content,
            content_type=message_data.content_type if message_data.content_type else "text",
            role=message_data.role,
            user_id=user_id
        )
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to create message"
            )
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error creating message: {str(e)}"
        ) 