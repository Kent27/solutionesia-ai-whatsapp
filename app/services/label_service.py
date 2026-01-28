import os
from typing import Optional, Dict, Any, List
from ..database.mysql import MariaDBClient
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LabelService:
    def __init__(self):
        self.db = MariaDBClient()
        
    async def get_labels(self, organization_id: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Get labels for an organization with pagination"""
        try:
            # Calculate offset
            offset = (page - 1) * limit
            
            # Get total count
            count_query = "SELECT COUNT(*) FROM labels WHERE organization_id = %s"
            count_result = await self.db.fetch_one(count_query, (organization_id,))
            total = count_result[0] if count_result else 0
            
            # Get labels
            query = """
                SELECT id, name, color, organization_id
                FROM labels
                WHERE organization_id = %s
                ORDER BY name ASC
                LIMIT %s OFFSET %s
            """
            results = await self.db.fetch_all(query, (organization_id, limit, offset))
            
            labels = []
            for row in results:
                labels.append({
                    "id": str(row[0]),
                    "name": row[1],
                    "color": row[2],
                    "organization_id": str(row[3])
                })
                
            return {
                "labels": labels,
                "total": total,
                "page": page,
                "limit": limit
            }
        except Exception as e:
            logger.error(f"Error getting labels: {str(e)}", exc_info=True)
            raise
            
    async def create_label(self, organization_id: str, name: str, color: str) -> Optional[Dict[str, Any]]:
        """Create a new label for an organization"""
        try:
            # Check if label with same name already exists for this organization
            check_query = "SELECT id FROM labels WHERE organization_id = %s AND name = %s"
            check_result = await self.db.fetch_one(check_query, (organization_id, name))
            
            if check_result:
                logger.warning(f"Label with name '{name}' already exists for organization {organization_id}")
                return None
                
            # Insert label
            query = """
                INSERT INTO labels (name, color, organization_id)
                VALUES (%s, %s, %s)
            """
            result = await self.db.execute(query, (name, color, organization_id))
            
            if result and result.get("id"):
                label_id = result.get("id")
                
                # Get the created label
                return await self.get_label_by_id(label_id)
            
            return None
        except Exception as e:
            logger.error(f"Error creating label: {str(e)}", exc_info=True)
            raise

    async def update_label(self, organization_id: str, label_id: str, name: str, color: str) -> Optional[Dict[str, Any]]:
        """Update a label"""
        try:
            # Check ownership
            check_query = "SELECT id FROM labels WHERE id = %s AND organization_id = %s"
            check_result = await self.db.fetch_one(check_query, (label_id, organization_id))
            
            if not check_result:
                return None

            # Update label
            query = """
                UPDATE labels 
                SET name = %s, color = %s, updated_at = NOW()
                WHERE id = %s AND organization_id = %s
            """
            await self.db.execute(query, (name, color, label_id, organization_id))
            
            return await self.get_label_by_id(label_id)
        except Exception as e:
            logger.error(f"Error updating label: {str(e)}", exc_info=True)
            raise

    async def delete_label(self, organization_id: str, label_id: str) -> bool:
        """Delete a label"""
        try:
             # Check ownership
            check_query = "SELECT id FROM labels WHERE id = %s AND organization_id = %s"
            check_result = await self.db.fetch_one(check_query, (label_id, organization_id))
            
            if not check_result:
                return False

            query = "DELETE FROM labels WHERE id = %s"
            await self.db.execute(query, (label_id,))
            return True
        except Exception as e:
            logger.error(f"Error deleting label: {str(e)}", exc_info=True)
            raise
            
    async def get_label_by_id(self, label_id: str) -> Optional[Dict[str, Any]]:
        """Get a label by ID"""
        try:
            query = """
                SELECT id, name, color, organization_id
                FROM labels
                WHERE id = %s
            """
            result = await self.db.fetch_one(query, (label_id,))
            
            if result:
                return {
                    "id": str(result[0]),
                    "name": result[1],
                    "color": result[2],
                    "organization_id": str(result[3])
                }
            
            return None
        except Exception as e:
            logger.error(f"Error getting label by ID: {str(e)}", exc_info=True)
            raise 

    async def assign_label(self, organization_id: str, contact_id: str, label_id: str) -> bool:
        """Assign a label to a contact"""
        try:
            # Verify contact belongs to organization
            contact_query = "SELECT id FROM contacts WHERE id = %s AND organization_id = %s"
            contact_check = await self.db.fetch_one(contact_query, (contact_id, organization_id))
            if not contact_check:
                raise ValueError("Contact does not belong to the organization")
                
            # Verify label belongs to organization
            label_query = "SELECT id FROM labels WHERE id = %s AND organization_id = %s"
            label_check = await self.db.fetch_one(label_query, (label_id, organization_id))
            if not label_check:
                raise ValueError("Label does not belong to the organization")
                
            # Check if assignment already exists
            check_query = "SELECT id FROM contact_labels WHERE contact_id = %s AND label_id = %s"
            existing = await self.db.fetch_one(check_query, (contact_id, label_id))
            if existing:
                return True # Already assigned
                
            # Assign
            insert_query = "INSERT INTO contact_labels (contact_id, label_id) VALUES (%s, %s)"
            await self.db.execute(insert_query, (contact_id, label_id))
            return True
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error assigning label: {str(e)}", exc_info=True)
            raise

    async def remove_label_from_contact(self, organization_id: str, contact_id: str, label_id: str) -> bool:
        """Remove a label from a contact"""
        try:
            # Verify contact belongs to organization (security check)
            contact_query = "SELECT id FROM contacts WHERE id = %s AND organization_id = %s"
            contact_check = await self.db.fetch_one(contact_query, (contact_id, organization_id))
            if not contact_check:
                raise ValueError("Contact does not belong to the organization")

            query = "DELETE FROM contact_labels WHERE contact_id = %s AND label_id = %s"
            await self.db.execute(query, (contact_id, label_id))
            return True
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error removing label from contact: {str(e)}", exc_info=True)
            raise    