from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path, status
from ..services.conversation_service import ConversationService
from ..services.websocket_service import manager
import jwt as pyjwt
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])
conversation_service = ConversationService()

@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: str
):
    try:
        # Get token from cookie (preferred) or query param
        token = websocket.cookies.get("access_token") or websocket.query_params.get("token")
        
        if not token:
            logger.warning(f"WebSocket connection rejected: Missing token for conversation {conversation_id}")
            # Note: browsers don't read close codes well, but 1008 is Policy Violation
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 1. Validate Token
        try:
            payload = pyjwt.decode(
                token, 
                os.getenv("JWT_SECRET_KEY", "your-secret-key"), 
                algorithms=["HS256"]
            )
            user_id = payload.get("sub")
            if not user_id:
                raise Exception("Invalid token payload")
        except Exception as e:
            logger.warning(f"WebSocket connection rejected: Invalid token - {str(e)}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 2. Check Permissions
        has_access = await conversation_service.verify_conversation_access(conversation_id, user_id)
        if not has_access:
            logger.warning(f"WebSocket connection rejected: User {user_id} has no access to conversation {conversation_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 3. Connect
        await manager.connect(websocket, conversation_id)
        logger.info(f"WebSocket connected: User {user_id} -> Conversation {conversation_id}")
        
        try:
            while True:
                # Keep connection alive and listen for incoming messages if any
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket, conversation_id)
            logger.info(f"WebSocket disconnected: User {user_id} -> Conversation {conversation_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            manager.disconnect(websocket, conversation_id)
            
    except Exception as e:
        logger.error(f"WebSocket connection setup error: {str(e)}")
        # If possible, close with error
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
