# from app.services.memory_service import MemoryService
import os
from typing import Optional, Dict, Any, List
from ..database.mysql import MariaDBClient
import logging
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class GetConversationResponse(BaseModel):
    id: str
    metadata: Dict[str, Any] | None = None
    status: str
    mode: str = 'ai'

class ConversationService:
    def __init__(self):
        self.db = MariaDBClient()

    async def get_conversation(self, contact_id: str, organization_id: str) -> Optional[GetConversationResponse]:
        """Get or create conversation by contact id and status 'active' """
        try:
            # Check if contact exists for the organization
            conversation_query = """
                SELECT conversations.id, conversations.metadata, conversations.status, conversations.mode
                FROM conversations 
                LEFT JOIN contacts 
                    ON conversations.contact_id = contacts.id
                WHERE conversations.contact_id = %s AND conversations.status = 'active' AND contacts.organization_id = %s
            """
            conversation = await self.db.fetch_one(conversation_query, (contact_id, organization_id))
            
            if conversation:
                return GetConversationResponse(
                    id=conversation[0],
                    metadata=conversation[1],
                    status=conversation[2],
                    mode=conversation[3] if conversation[3] else 'ai'
                )

            return None
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}", exc_info=True)
            raise
    
    async def update_conversation_mode(self, id: str, mode: str) -> bool:
        """Update conversation mode to 'ai' or 'human' """
        try:
            update_query = """
                UPDATE conversations 
                SET mode = %s 
                WHERE id = %s
            """
            await self.db.execute(update_query, (mode, id))
            return True
        except Exception as e:
            logger.error(f"Error updating conversation mode: {str(e)}", exc_info=True)
            raise Exception("Failed to update conversation mode")

    async def update_conversation_status(self, id: str, status: str) -> bool:
        """Update conversation mode to 'ai' or 'human' """
        try:
            # Ensure single 'active' conversation
            if status == 'active':
                query = """
                    SELECT id 
                    FROM conversations 
                    WHERE id = %s AND status = 'active'
                """

                result = await self.db.fetch_one(query, (id,))

                if result:
                    raise Exception("Another conversation is 'active'")
            
            update_query = """
                UPDATE conversations 
                SET status = %s 
                WHERE id = %s
            """
            
            await self.db.execute(update_query, (status, id))

            return True
        except Exception as e:
            logger.error(f"Error updating conversation mode: {str(e)}", exc_info=True)
            raise Exception("Failed to update conversation status")

    
    async def insert_conversation(self, id: str, contact_id: str, mode: str) -> GetConversationResponse:
        """Create a new conversation"""
        try:
            insert_query = """
                INSERT INTO conversations (id, contact_id, status, mode)
                VALUES (%s, %s, 'active', %s)
            """
            await self.db.execute(insert_query, (id, contact_id, mode))
            
            fetch_query = """
                SELECT id, metadata, status, mode
                FROM conversations 
                WHERE contact_id = %s AND status = 'active'
                ORDER BY id DESC
                LIMIT 1
            """
            conversation = await self.db.fetch_one(fetch_query, (contact_id,))
            
            if conversation:
                return GetConversationResponse(
                    id=conversation[0],
                    metadata=conversation[1],
                    status=conversation[2],
                    mode=conversation[3]
                )
            else:
                raise Exception("Failed to create conversation")
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}", exc_info=True)
            raise
    
    async def insert_message(self, contact_id: str, conversation_id: str, contents: List[Dict[str, Any]], role: str):
        """Insert messages into conversation"""
        try:
            # memory_service = MemoryService(contact_id)

            insert_query = """
                INSERT INTO messages (conversation_id, content, content_type, role)
                VALUES (%s, %s, %s, %s)
            """
            
            data_to_insert = []

            for item in contents:
                type = item.get('type')

                if type == 'text':
                    content = item.get('text')
                elif type == 'image':
                    content = item.get('image')
                elif type == 'video':
                    content = item.get('video')
                elif type == 'audio':
                    content = item.get('audio')
                elif type == 'file':
                    content = item.get('file')
                else:
                    content = item.get('content')
                    
                row = (conversation_id, content, type, role)
                data_to_insert.append(row)

                # memory_service.add_message(
                #     role=role,
                #     content=str(content),
                #     conversation_id=conversation_id,
                #     timestamp=datetime.now().isoformat()
                # )

            pool = await self.db.get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.executemany(insert_query, data_to_insert)
                    await conn.commit()
                               
        except Exception as e:
            logger.error(f"Error bulk inserting messages: {str(e)}", exc_info=True)
            raise

conversation_service = ConversationService()

# Expose functions at module level for backward compatibility
get_conversation = conversation_service.get_conversation
insert_message = conversation_service.insert_message
insert_conversation = conversation_service.insert_conversation
update_conversation_mode = conversation_service.update_conversation_mode
update_conversation_status = conversation_service.update_conversation_status
