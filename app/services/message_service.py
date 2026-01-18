import os
from typing import Optional, Dict, Any, List
from ..database.mysql import MariaDBClient
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageService:
    def __init__(self):
        self.db = MariaDBClient()
        
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
            
    async def create_message(self, user_id: str, content: str, recipient_id: str, recipient_type: str) -> Optional[Dict[str, Any]]:
        """Create a new message"""
        try:
            # Insert message
            query = """
                INSERT INTO messages (content, sender_id, recipient_id, recipient_type, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            result = await self.db.execute(query, (content, user_id, recipient_id, recipient_type, "pending"))
            
            if result and result.get("id"):
                message_id = result.get("id")
                
                # Get the created message
                get_query = """
                    SELECT id, content, timestamp, status, recipient_id, recipient_type
                    FROM messages
                    WHERE id = %s
                """
                message = await self.db.fetch_one(get_query, (message_id,))
                
                if message:
                    # Send the message via WhatsApp service
                    # This would be implemented based on your WhatsApp integration
                    # await self.send_whatsapp_message(message)
                    
                    return {
                        "id": str(message[0]),
                        "content": message[1],
                        "timestamp": message[2],
                        "status": message[3],
                        "recipientId": message[4],
                        "recipientType": message[5]
                    }
            
            return None
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