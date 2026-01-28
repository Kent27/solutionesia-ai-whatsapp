import openai.types.beta.realtime.response_audio_delta_event
from app.services.conversation_service import insert_message
import json
from app.services.websocket_service import manager
import os
from typing import Optional, Dict, Any, List
from ..database.mysql import MariaDBClient
import logging
from datetime import datetime
from ..services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


class MessageService:
    def __init__(self):
        self.db = MariaDBClient()
        self.whatsapp_service = WhatsAppService()

    async def get_messages(
        self, user_id: str, page: int = 1, limit: int = 50
    ) -> Dict[str, Any]:
        """Get messages for a user with pagination"""
        try:
            # Calculate offset
            offset = (page - 1) * limit

            # Get total count
            count_query = "SELECT COUNT(*) FROM messages WHERE sender_id = %s"
            count_result = await self.db.fetch_one(count_query, (user_id,))
            total = count_result[0] if count_result else 0

            # Get messages
            query = """
                SELECT id, content, timestamp, status, recipient_id, recipient_type
                FROM messages
                WHERE sender_id = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            results = await self.db.fetch_all(query, (user_id, limit, offset))

            messages = []
            for row in results:
                messages.append(
                    {
                        "id": str(row[0]),
                        "content": row[1],
                        "timestamp": row[2],
                        "status": row[3],
                        "recipientId": row[4],
                        "recipientType": row[5],
                    }
                )

            return {"messages": messages, "total": total, "page": page, "limit": limit}
        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}", exc_info=True)
            raise

    async def create_message(
        self,
        conversation_id: str,
        content: str,
        content_type: str = "text",
        role: str = "admin",
        user_id: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new message in a conversation"""
        try:
            # Get contact_id from conversation to set recipient
            conv_query = "SELECT contact_id FROM conversations WHERE id = %s"
            conv = await self.db.fetch_one(conv_query, (conversation_id,))

            if not conv:
                raise Exception("Contact not found")

            get_conversation_query = """
                SELECT o.id, o.phone_id, c.phone_number
                FROM organizations o
                JOIN contacts c ON o.id = c.organization_id
                JOIN conversations conv ON c.id = conv.contact_id
                WHERE conv.id = %s
            """

            row = await self.db.fetch_one(get_conversation_query, (conversation_id,))
            if not row:
                raise Exception("Conversation not found")

            org_id = row[0]
            org_phone_number = row[1]
            org_contact_number = row[2]

            # Send to WhatsApp
            result_wa = await self.whatsapp_service.send_message(
                phone_id=org_phone_number, to=org_contact_number, message=content
            )

            org_user_query = """
                SELECT phone_number
                FROM organization_users
                WHERE organization_id = %s AND user_id = %s
            """

            org_user = await self.db.fetch_one(org_user_query, (org_id, user_id))
            if not org_user:
                raise Exception("Organization user not found")

            org_user_phone_number = org_user[0]

            # Adding admin identity to remark
            remark = f"admin:{org_user_phone_number}"

            # Insert to DB
            await insert_message(
                conversation_id=conversation_id,
                contents=[{"text": content, "type": content_type}],
                role=role,
                remark=remark
            )

            # Broadcast message to websocket
            status = "sent"
            message = json.dumps(
                {
                    "broadcast_type": "new_message",
                    "content": content,
                    "content_type": content_type,
                    "role": role,
                    "status": status,
                    "timestamp": str(datetime.now()),
                }
            )
            await manager.broadcast(message, conversation_id)

            if not result_wa:
                raise Exception("Failed to send WhatsApp Message")

            return {
                "conversation_id": conversation_id,
                "content": content,
                "content_type": content_type,
                "role": role,
                "timestamp": str(datetime.now()),
                "status": status,
            }

        except Exception as e:
            logger.error(f"Error creating message: {str(e)}", exc_info=True)
            raise

    async def update_message_status(self, message_id: str, status: str) -> bool:
        """Update message status"""
        try:
            query = "UPDATE messages SET status = %s WHERE id = %s"
            result = await self.db.execute(query, (status, message_id))
            return result is not None
        except Exception as e:
            logger.error(f"Error updating message status: {str(e)}", exc_info=True)
            return False
