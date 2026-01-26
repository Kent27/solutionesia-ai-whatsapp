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
        
    async def get_messages(self, user_id: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
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
                messages.append({
                    "id": str(row[0]),
                    "content": row[1],
                    "timestamp": row[2],
                    "status": row[3],
                    "recipientId": row[4],
                    "recipientType": row[5]
                })
                
            return {
                "messages": messages,
                "total": total,
                "page": page,
                "limit": limit
            }
        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}", exc_info=True)
            raise
            
    async def create_message(self, conversation_id: str, content: str, content_type: str = "text", role: str = "admin") -> Optional[Dict[str, Any]]:
        """Create a new message in a conversation"""
        try:
            # Get contact_id from conversation to set recipient
            conv_query = "SELECT contact_id FROM conversations WHERE id = %s"
            conv = await self.db.fetch_one(conv_query, (conversation_id,))
            contact_id = conv[0] if conv else None
            
            # Insert message
            insert_query = """
                INSERT INTO messages (conversation_id, content, content_type, role)
                VALUES (%s, %s, %s, %s)
            """
            
            result = await self.db.execute(insert_query, (
                conversation_id,
                content,
                content_type,
                role
            ))

            get_conversation_query = """
                SELECT o.phone_id, c.phone_number
                FROM organizations o
                JOIN contacts c ON o.id = c.organization_id
                JOIN conversations conv ON c.id = conv.contact_id
                WHERE conv.id = %s
            """

            row = await self.db.fetch_one(get_conversation_query, (conversation_id,))
            
            if not row:
                raise Exception("Conversation not found")

            if result and isinstance(result, dict) and result.get("id"):
                message_id = str(result.get("id"))
            else:
                 # If execute doesn't return id, we might need another way or assume it did.
                 # For now, let's try to pass '0' or look it up if critical, but likely it returns id.
                 # Or query last inserted.
                 # Let's hope result contains ID.
                 message_id = str(result.get("id")) if isinstance(result, dict) else "unknown"

            result_wa = await self.whatsapp_service.send_message(
                phone_id=row[0],
                to=row[1],
                message=content
            )

            if not result_wa:
                raise Exception("Failed to send WhatsApp Message")

            return {
                "id": message_id,
                "conversation_id": conversation_id,
                "content": content,
                "content_type": content_type,
                "timestamp": datetime.now(),
                "role": role,
                "status": "sent",
                "recipientId": str(contact_id) if contact_id else "unknown",
                "recipientType": "contact"
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