import os
from typing import Optional, Dict, Any, List
from ..database.mysql import MariaDBClient
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LabelService:
    def __init__(self):
        self.db = MariaDBClient()
        
    async def get_labels(self, user_id: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Get labels for a user with pagination"""
        try:
            # Calculate offset
            offset = (page - 1) * limit
            
            # Get total count
            count_query = "SELECT COUNT(*) FROM labels WHERE user_id = %s"
            count_result = await self.db.fetch_one(count_query, (user_id,))
            total = count_result[0] if count_result else 0
            
            # Get labels
            query = """
                SELECT id, name, color
                FROM labels
                WHERE user_id = %s
                ORDER BY name ASC
                LIMIT %s OFFSET %s
            """
            results = await self.db.fetch_all(query, (user_id, limit, offset))
            
            labels = []
            for row in results:
                labels.append({
                    "id": str(row[0]),
                    "name": row[1],
                    "color": row[2]
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
            
    async def create_label(self, user_id: str, name: str, color: str) -> Optional[Dict[str, Any]]:
        """Create a new label"""
        try:
            # Check if label with same name already exists for this user
            check_query = "SELECT id FROM labels WHERE user_id = %s AND name = %s"
            check_result = await self.db.fetch_one(check_query, (user_id, name))
            
            if check_result:
                logger.warning(f"Label with name '{name}' already exists for user {user_id}")
                return None
                
            # Insert label
            query = """
                INSERT INTO labels (name, color, user_id)
                VALUES (%s, %s, %s)
            """
            result = await self.db.execute(query, (name, color, user_id))
            
            if result and result.get("id"):
                label_id = result.get("id")
                
                # Get the created label
                return await self.get_label_by_id(label_id)
            
            return None
        except Exception as e:
            logger.error(f"Error creating label: {str(e)}", exc_info=True)
            raise
            
    async def get_label_by_id(self, label_id: str) -> Optional[Dict[str, Any]]:
        """Get a label by ID"""
        try:
            query = """
                SELECT id, name, color
                FROM labels
                WHERE id = %s
            """
            result = await self.db.fetch_one(query, (label_id,))
            
            if result:
                return {
                    "id": str(result[0]),
                    "name": result[1],
                    "color": result[2]
                }
            
            return None
        except Exception as e:
            logger.error(f"Error getting label by ID: {str(e)}", exc_info=True)
            raise 