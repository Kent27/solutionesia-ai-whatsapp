from typing import Optional, Dict, Any, List
from ..database.mysql import MariaDBClient
import logging

logger = logging.getLogger(__name__)

class ContactService:
    def __init__(self):
        self.db = MariaDBClient()
        
    async def get_contact_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get a contact by phone number"""
        try:
            query = """
                SELECT id, name, phone_number, user_id, chat_status, thread_id, stamps
                FROM contacts
                WHERE phone_number = %s
            """
            result = await self.db.fetch_one(query, (phone_number,))
            
            if result:
                return {
                    "id": str(result[0]),
                    "name": result[1],
                    "phoneNumber": result[2],
                    "user_id": str(result[3]) if result[3] else None,
                    "chat_status": result[4],
                    "thread_id": result[5],
                    "stamps": result[6] or 0
                }
            
            return None
        except Exception as e:
            logger.error(f"Error getting contact by phone number: {str(e)}", exc_info=True)
            raise
            
    async def set_chat_status(self, phone_number: str, status: str) -> bool:
        """
        Set the chat status for a contact
        
        Args:
            phone_number: The contact's phone number
            status: The status to set (e.g., "Live Chat")
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the contact by phone number
            contact = await self.get_contact_by_phone(phone_number)
            if not contact:
                logger.warning(f"Contact not found for phone number: {phone_number}")
                return False
                
            # Update the chat status
            query = """
                UPDATE contacts
                SET chat_status = %s, updated_at = NOW()
                WHERE id = %s
            """
            await self.db.execute(query, (status, contact['id']))
            logger.info(f"Updated chat status to '{status}' for contact {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting chat status: {str(e)}", exc_info=True)
            return False
            
    async def update_thread_id(self, phone_number: str, thread_id: str) -> bool:
        """
        Update the OpenAI thread ID for a contact
        
        Args:
            phone_number: The contact's phone number
            thread_id: The new thread ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the contact by phone number
            contact = await self.get_contact_by_phone(phone_number)
            if not contact:
                logger.warning(f"Contact not found for phone number: {phone_number}")
                return False
                
            # Skip update if thread ID is the same
            if contact.get('thread_id') == thread_id:
                return True
                
            # Update the thread ID
            query = """
                UPDATE contacts
                SET thread_id = %s, updated_at = NOW()
                WHERE id = %s
            """
            await self.db.execute(query, (thread_id, contact['id']))
            logger.info(f"Updated thread ID for contact {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating thread ID: {str(e)}", exc_info=True)
            return False
    
    async def get_contacts(self, user_id: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Get contacts for a user with pagination"""
        try:
            # Calculate offset
            offset = (page - 1) * limit
            
            # Get total count
            count_query = "SELECT COUNT(*) FROM contacts WHERE user_id = %s"
            count_result = await self.db.fetch_one(count_query, (user_id,))
            total = count_result[0] if count_result else 0
            
            # Get contacts
            query = """
                SELECT id, name, phone_number
                FROM contacts
                WHERE user_id = %s
                ORDER BY name ASC
                LIMIT %s OFFSET %s
            """
            results = await self.db.fetch_all(query, (user_id, limit, offset))
            
            contacts = []
            for row in results:
                contact_id = row[0]
                
                # Get labels for this contact
                labels_query = """
                    SELECT l.id
                    FROM labels l
                    JOIN contact_labels cl ON l.id = cl.label_id
                    WHERE cl.contact_id = %s
                """
                labels_results = await self.db.fetch_all(labels_query, (contact_id,))
                labels = [str(label[0]) for label in labels_results]
                
                contacts.append({
                    "id": str(contact_id),
                    "name": row[1],
                    "phoneNumber": row[2],
                    "labels": labels
                })
                
            return {
                "contacts": contacts,
                "total": total,
                "page": page,
                "limit": limit
            }
        except Exception as e:
            logger.error(f"Error getting contacts: {str(e)}", exc_info=True)
            raise
            
    async def create_contact(self, user_id: str, name: str, phone_number: str, labels: List[str] = None) -> Optional[Dict[str, Any]]:
        """Create a new contact"""
        try:
            # Insert contact
            query = """
                INSERT INTO contacts (name, phone_number, user_id)
                VALUES (%s, %s, %s)
            """
            result = await self.db.execute(query, (name, phone_number, user_id))
            
            if result and result.get("id"):
                contact_id = result.get("id")
                
                # Add labels if provided
                if labels and len(labels) > 0:
                    for label_id in labels:
                        await self.add_label_to_contact(contact_id, label_id)
                
                # Get the created contact
                return await self.get_contact_by_id(contact_id)
            
            return None
        except Exception as e:
            logger.error(f"Error creating contact: {str(e)}", exc_info=True)
            raise
            
    async def get_contact_by_id(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get a contact by ID"""
        try:
            query = """
                SELECT id, name, phone_number, user_id
                FROM contacts
                WHERE id = %s
            """
            result = await self.db.fetch_one(query, (contact_id,))
            
            if result:
                # Get labels for this contact
                labels_query = """
                    SELECT l.id
                    FROM labels l
                    JOIN contact_labels cl ON l.id = cl.label_id
                    WHERE cl.contact_id = %s
                """
                labels_results = await self.db.fetch_all(labels_query, (contact_id,))
                labels = [str(label[0]) for label in labels_results]
                
                return {
                    "id": str(result[0]),
                    "name": result[1],
                    "phoneNumber": result[2],
                    "user_id": str(result[3]) if result[3] else None,
                    "labels": labels
                }
            
            return None
        except Exception as e:
            logger.error(f"Error getting contact by ID: {str(e)}", exc_info=True)
            raise
            
    async def add_label_to_contact(self, contact_id: str, label_id: str) -> bool:
        """Add a label to a contact"""
        try:
            # Check if the label exists
            label_query = "SELECT id FROM labels WHERE id = %s"
            label_result = await self.db.fetch_one(label_query, (label_id,))
            
            if not label_result:
                logger.warning(f"Label {label_id} does not exist")
                return False
                
            # Check if the contact exists
            contact_query = "SELECT id FROM contacts WHERE id = %s"
            contact_result = await self.db.fetch_one(contact_query, (contact_id,))
            
            if not contact_result:
                logger.warning(f"Contact {contact_id} does not exist")
                return False
                
            # Check if the label is already assigned to the contact
            check_query = """
                SELECT 1 FROM contact_labels
                WHERE contact_id = %s AND label_id = %s
            """
            check_result = await self.db.fetch_one(check_query, (contact_id, label_id))
            
            if check_result:
                logger.info(f"Label {label_id} already assigned to contact {contact_id}")
                return True
                
            # Add the label to the contact
            query = """
                INSERT INTO contact_labels (contact_id, label_id)
                VALUES (%s, %s)
            """
            await self.db.execute(query, (contact_id, label_id))
            
            return True
        except Exception as e:
            logger.error(f"Error adding label to contact: {str(e)}", exc_info=True)
            return False 