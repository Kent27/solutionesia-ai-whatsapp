from app.models.organization_models import GetOrganizationResponse
import logging
import secrets
import string
from typing import Optional, Dict, Any
from ..database.mysql import MariaDBClient
from ..models.organization_models import OrganizationCreate, OrganizationUpdateStatus, OrganizationUpdateProfile
from .organization_auth_service import OrganizationAuthService

logger = logging.getLogger(__name__)

class OrganizationService:
    def __init__(self):
        self.db = MariaDBClient()
        self.auth_service = OrganizationAuthService()
    
    async def get_organization_by_phone_id(self, phone_id: str) -> Optional[GetOrganizationResponse]:
        """Get organization by phone_id"""
        try:
            query = "SELECT id, name, email, status FROM organizations WHERE phone_id = %s"
            result = await self.db.fetch_one(query, (phone_id,))
            
            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "email": result[2],
                    "status": result[3]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting organization by email: {str(e)}")
            return None

    def _generate_random_password(self, length=12):
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for i in range(length))

    async def create_organization(self, org_data: OrganizationCreate) -> Optional[Dict[str, Any]]:
        """Create a new organization"""
        try:
            # Check if email exists
            existing_org = await self.auth_service.get_organization_by_email(org_data.email)
            if existing_org:
                raise ValueError("Email already registered")

            # Handle password
            plain_password = org_data.password
            if not plain_password:
                plain_password = self._generate_random_password()
            
            hashed_password = self.auth_service.get_password_hash(plain_password)
            
            # Default status
            status = 'pending'

            query = """
                INSERT INTO organizations (name, email, phone_id, password, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            await self.db.execute(query, (
                org_data.name,
                org_data.email,
                org_data.phone_id,
                hashed_password,
                status
            ))
            
            # Fetch created org
            org = await self.auth_service.get_organization_by_email(org_data.email)
            
            if org:
                # Return plain password so it can be shown once if it was generated
                # or just as confirmation
                org['plain_password_if_generated'] = plain_password if not org_data.password else None
                return org
                
            return None

        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Error creating organization: {str(e)}", exc_info=True)
            raise

    async def update_status(self, org_id: str, status_data: OrganizationUpdateStatus) -> Optional[Dict[str, Any]]:
        """Update organization status (Admin)"""
        try:
            query = "UPDATE organizations SET status = %s WHERE id = %s"
            await self.db.execute(query, (status_data.status, org_id))
            
            # Fetch updated
            query_get = "SELECT id, name, email, status FROM organizations WHERE id = %s"
            result = await self.db.fetch_one(query_get, (org_id,))
            
            if result:
                return {
                    "id": str(result[0]),
                    "name": result[1],
                    "email": result[2],
                    "status": result[3],
                    "phone_id": result[4],
                    "created_at": result[5],
                    "updated_at": result[6]
                }
            return None
        except Exception as e:
            logger.error(f"Error updating organization status: {str(e)}", exc_info=True)
            raise

    async def update_profile(self, org_id: str, profile_data: OrganizationUpdateProfile) -> Optional[Dict[str, Any]]:
        """Update organization profile"""
        try:
            updates = []
            params = []
            
            if profile_data.name:
                updates.append("name = %s")
                params.append(profile_data.name)
            
            if profile_data.password:
                hashed = self.auth_service.get_password_hash(profile_data.password)
                updates.append("password = %s")
                params.append(hashed)
            
            if not updates:
                return None
                
            query = f"UPDATE organizations SET {', '.join(updates)} WHERE id = %s"
            params.append(org_id)
            
            await self.db.execute(query, tuple(params))
            
            query_get = "SELECT id, name, email, status, phone_id, created_at, updated_at FROM organizations WHERE id = %s"
            result = await self.db.fetch_one(query_get, (org_id,))
            
            if result:
                return {
                    "id": str(result[0]),
                    "name": result[1],
                    "email": result[2],
                    "status": result[3],
                    "phone_id": result[4],
                    "created_at": result[5],
                    "updated_at": result[6]
                }
            return None
        except Exception as e:
            logger.error(f"Error updating organization profile: {str(e)}", exc_info=True)
            raise
