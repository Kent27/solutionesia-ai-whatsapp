from app.services.organization_permission_service import OrganizationPermissionService
from app.services.organization_service import OrganizationService
import os
from typing import Optional, Dict, Any, List
from ..database.mysql import MariaDBClient
import logging
from datetime import datetime
from pydantic import BaseModel
import json
from .websocket_service import manager

logger = logging.getLogger(__name__)


class GetConversationResponse(BaseModel):
    id: str
    name: str = "Unknown"
    phoneNumber: Optional[str] = None
    status: str
    mode: str
    contact: Optional[Dict[str, Any]] = None
    messages: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class ConversationService:
    def __init__(self):
        self.db = MariaDBClient()

    async def verify_conversation_access(
        self, conversation_id: str, user_id: str
    ) -> bool:
        """Verify if a user has access to a conversation (Org Member OR App Admin)"""
        try:
            org_service = OrganizationService()

            org_id = await org_service.get_organization_id_by_conversation_id(
                conversation_id
            )
            is_org_user = await org_service.check_is_org_member(org_id, user_id)

            return is_org_user
        except Exception as e:
            logger.error(
                f"Error verification conversation access: {str(e)}", exc_info=True
            )
            return False

    async def can_be_opened(self, conversation_id: str) -> bool:
        """Get or create conversation by contact id and status 'active'"""
        try:
            # Check if contact exists for the organization
            conversation_query = """
                SELECT 1
                FROM conversations 
                WHERE conversations.id = %s AND conversations.status = 'active' AND conversations.mode = 'human' and conversations.is_opened = false
            """
            conversation = await self.db.exists(conversation_query, (conversation_id,))

            return conversation
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}", exc_info=True)
            raise

    async def can_open_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Verify if a user has access to a conversation (Org Admin or Org User with 'takeover' permission)"""
        try:
            org_service = OrganizationService()
            org_permission_service = OrganizationPermissionService()

            org_id = await org_service.get_organization_id_by_conversation_id(
                conversation_id
            )

            is_org_admin = await org_service.check_is_org_admin(org_id, user_id)
            if is_org_admin:
                return True

            is_org_user = await org_service.check_is_org_member(org_id, user_id)
            permitted = await org_permission_service.check_org_permission(
                org_id, user_id, "takeover"
            )

            return is_org_user and permitted
        except Exception as e:
            logger.error(
                f"Error verification conversation access: {str(e)}", exc_info=True
            )
            return False

    async def get_conversation(
        self, contact_id: str, organization_id: str
    ) -> Optional[GetConversationResponse]:
        """Get or create conversation by contact id and status 'active'"""
        try:
            # Check if contact exists for the organization
            conversation_query = """
                SELECT conversations.id, conversations.status, conversations.mode
                FROM conversations 
                LEFT JOIN contacts 
                    ON conversations.contact_id = contacts.id
                WHERE conversations.contact_id = %s AND conversations.status = 'active' AND contacts.organization_id = %s
            """
            conversation = await self.db.fetch_one(
                conversation_query, (contact_id, organization_id)
            )

            if conversation:
                return GetConversationResponse(
                    id=conversation[0],
                    status=conversation[1],
                    mode=conversation[2] if conversation[2] else "ai",
                )

            return None
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}", exc_info=True)
            raise

    async def get_conversation_details(
        self, conversation_id: str
    ) -> Optional[GetConversationResponse]:
        """Get conversation details by ID"""
        try:
            query = """
                SELECT c.id, c.status, c.mode,
                       ct.id as contact_id, ct.name, ct.phone_number
                FROM conversations c
                LEFT JOIN contacts ct ON c.contact_id = ct.id
                WHERE c.id = %s
            """
            row = await self.db.fetch_one(query, (conversation_id,))

            if row:
                # Prepare contact info
                contact_name = row[4] if row[4] else "Unknown"
                contact_phone = row[5] if row[5] else ""

                # Fix phone format
                if (
                    contact_phone
                    and not contact_phone.startswith("+")
                    and contact_phone.isdigit()
                ):
                    contact_phone = f"+{contact_phone}"
                elif contact_phone and not contact_phone.startswith("+"):
                    # attempt to fix clean
                    import re  # ensure imported or use simple check

                    # assuming it might just be numbers
                    pass

                contact_data = None
                if row[3]:  # contact_id exists
                    contact_data = {
                        "id": str(row[3]),
                        "name": contact_name,
                        "phoneNumber": contact_phone,
                    }

                # Fetch messages
                msg_query = """
                    SELECT content, content_type, status, role, created_at
                    FROM messages
                    WHERE conversation_id = %s
                """
                msg_rows = await self.db.fetch_all(msg_query, (conversation_id,))

                messages = []
                for m in msg_rows:
                    messages.append(
                        {
                            "content": m[0] if m[0] else "",
                            "contentType": m[1],
                            "role": m[3] if m[3] else "unknown",
                            "status": m[2],
                            "timestamp": m[4],
                        }
                    )

                return GetConversationResponse(
                    id=str(row[0]),
                    name=contact_name,
                    phoneNumber=contact_phone,
                    status=row[1],
                    mode=row[2] if row[2] else "ai",
                    contact=contact_data,
                    messages=messages,
                )
            return None
        except Exception as e:
            logger.error(f"Error getting conversation details: {str(e)}", exc_info=True)
            raise

    async def update_conversation_mode(self, id: str, mode: str) -> bool:
        """Update conversation mode to 'ai' or 'human'"""
        try:
            update_query = """
                UPDATE conversations 
                SET mode = %s 
                WHERE id = %s
            """
            await self.db.execute(update_query, (mode, id))

            # Mark chat as 'new' on 'human' mode
            # otherwise, mark as 'always read' on 'ai' mode
            # FE needs to notify the 'opened' status back
            await self.update_conversation_open_status(id, False)

            logger.info(f"Conversation mode updated to {mode} for conversation {id}")
            return True
        except Exception as e:
            logger.error(f"Error updating conversation mode: {str(e)}", exc_info=True)
            raise Exception("Failed to update conversation mode")

    async def update_conversation_open_status(
        self, id: str, is_opened: bool = True
    ) -> bool:
        """Update conversation open status"""
        try:
            update_query = """
                UPDATE conversations 
                SET is_opened = %s 
                WHERE id = %s
            """
            await self.db.execute(update_query, (is_opened, id))

            logger.info(
                f"Conversation open status updated to {str(is_opened)} for conversation {id}"
            )
            return True
        except Exception as e:
            logger.error(f"Error updating conversation mode: {str(e)}", exc_info=True)
            raise Exception("Failed to update conversation mode")

    async def update_conversation_mode_by_contact(
        self, phone_number: str, organization_id: str, mode: str
    ) -> bool:
        """Update conversation mode to 'ai' or 'human'"""
        try:
            get_conversation_query = """
                SELECT conversations.id 
                FROM conversations 
                JOIN contacts ON conversations.contact_id = contacts.id
                JOIN organizations ON contacts.organization_id = organizations.id
                WHERE contacts.phone_number = %s 
                AND organizations.id = %s
                AND conversations.status = 'active'
            """

            conversation = await self.db.fetch_one(
                get_conversation_query, (phone_number, organization_id)
            )

            if not conversation:
                raise Exception("Conversation not found")

            conversation_id = conversation[0]

            update_query = """
                UPDATE conversations 
                SET mode = %s 
                WHERE id = %s
            """
            await self.db.execute(update_query, (mode, conversation_id))

            # Notify active clients via websocket
            message = json.dumps(
                {
                    "broadcast_type": "conversation_mode_update",
                    "mode": mode,
                    "timestamp": str(datetime.now()),
                }
            )
            await manager.broadcast(message, conversation_id)

            logger.info(
                f"Conversation mode updated to {mode} for conversation {conversation_id}"
            )

            return True
        except Exception as e:
            logger.error(f"Error updating conversation mode: {str(e)}", exc_info=True)
            raise Exception("Failed to update conversation mode")

    async def update_conversation_status(self, id: str, status: str) -> bool:
        """Update conversation mode to 'ai' or 'human'"""
        try:
            # Ensure single 'active' conversation
            if status == "active":
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

    async def insert_conversation(
        self, id: str, contact_id: str, mode: str
    ) -> GetConversationResponse:
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
                response = GetConversationResponse(
                    id=conversation[0],
                    metadata=conversation[1],
                    status=conversation[2],
                    mode=conversation[3],
                )

                # Broadcast new conversation event
                await manager.broadcast(
                    json.dumps(
                        {"type": "conversation_created", "data": response.model_dump()}
                    ),
                    id,
                )

                return response
            else:
                raise Exception("Failed to create conversation")
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}", exc_info=True)
            raise

    async def insert_message(
        self,
        conversation_id: str,
        contents: List[Dict[str, Any]],
        role: str,
        remark: str | None = None,
    ):
        """Insert messages into conversation"""
        try:
            if remark:
                insert_query = """
                    INSERT INTO messages (conversation_id, content, content_type, role, remark)
                    VALUES (%s, %s, %s, %s, %s)
                """
            else:
                insert_query = """
                    INSERT INTO messages (conversation_id, content, content_type, role)
                    VALUES (%s, %s, %s, %s)
                """

            data_to_insert = []

            for item in contents:
                type = item.get("type")

                if type == "text":
                    content = item.get("text")
                elif type == "image":
                    content = item.get("image")
                elif type == "video":
                    content = item.get("video")
                elif type == "audio":
                    content = item.get("audio")
                elif type == "file":
                    content = item.get("file")
                else:
                    content = item.get("content")

                if remark:
                    row = (conversation_id, content, type, role, remark)
                else:
                    row = (conversation_id, content, type, role)

                data_to_insert.append(row)

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
update_conversation_mode_by_contact = (
    conversation_service.update_conversation_mode_by_contact
)
update_conversation_status = conversation_service.update_conversation_status
