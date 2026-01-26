from app.routers.auth import auth_service
from app.models.organization_models import GetOrganizationResponse
import logging
from typing import Optional, Dict, Any, List
from ..database.mysql import MariaDBClient
from ..models.organization_models import OrganizationCreate, OrganizationUpdateStatus, OrganizationUpdateProfile, ConversationFilter

logger = logging.getLogger(__name__)

class OrganizationService:
    def __init__(self):
        self.db = MariaDBClient()

    async def get_organization_human_conversations(self, org_id: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get 'human' mode conversations for an organization"""
        try:
            offset = (page - 1) * limit
            
            # Count
            count_query = """
                SELECT COUNT(c.id) 
                FROM conversations c
                JOIN contacts ct ON c.contact_id = ct.id
                WHERE ct.organization_id = %s AND c.mode = 'human'
            """
            count_res = await self.db.fetch_one(count_query, (org_id,))
            total = count_res[0] if count_res else 0
            
            # Fetch
            query = """
                SELECT c.id, ct.name, ct.phone_number, c.metadata, c.status, c.mode,
                       (SELECT content FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user' ORDER BY m.created_at DESC LIMIT 1) as last_user_message,
                       (SELECT created_at FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user' ORDER BY m.created_at DESC LIMIT 1) as last_user_message_at
                FROM conversations c
                JOIN contacts ct ON c.contact_id = ct.id
                WHERE ct.organization_id = %s AND c.mode = 'human'
                ORDER BY c.id DESC
                LIMIT %s OFFSET %s
            """
            rows = await self.db.fetch_all(query, (org_id, limit, offset))
            
            conversations = []
            for cr in rows:
                conversations.append({
                    "id": str(cr[0]),
                    "name": str(cr[1]),
                    "phoneNumber": str(cr[2]),
                    "metadata": cr[3],
                    "status": cr[4],
                    "mode": cr[5],
                    "lastMessage": cr[6],
                    "timestamp": cr[7]
                })
                
            return {
                "conversations": conversations,
                "total": total,
                "page": page,
                "limit": limit
            }
        except Exception as e:
            logger.error(f"Error getting organization human conversations: {str(e)}", exc_info=True)
            raise

    async def get_organization_conversations(self, org_id: str, filter: ConversationFilter) -> Dict[str, Any]:
        """Get conversations for an organization with optional filters"""
        try:
            offset = (filter.page - 1) * filter.limit
            params = [org_id]
            conditions = ["ct.organization_id = %s"]
            
            if filter.mode:
                conditions.append("c.mode = %s")
                params.append(filter.mode)
            
            if filter.status:
                conditions.append("c.status = %s")
                params.append(filter.status)
            
            where_clause = "WHERE " + " AND ".join(conditions)
            
            # Count
            count_query = f"""
                SELECT COUNT(c.id) 
                FROM conversations c
                JOIN contacts ct ON c.contact_id = ct.id
                {where_clause}
            """
            count_res = await self.db.fetch_one(count_query, tuple(params))
            total = count_res[0] if count_res else 0
            
            if total == 0:
                 return {
                    "conversations": [],
                    "total": 0,
                    "page": filter.page,
                    "limit": filter.limit
                }

            # Fetch
            params.append(filter.limit)
            params.append(offset)
            
            query = f"""
                SELECT c.id, c.status, c.mode,
                       ct.id as contact_id, ct.name, ct.phone_number,
                       (SELECT content FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user' ORDER BY m.created_at DESC LIMIT 1) as last_message,
                       (SELECT created_at FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user' ORDER BY m.created_at DESC LIMIT 1) as timestamp
                FROM conversations c
                JOIN contacts ct ON c.contact_id = ct.id
                {where_clause}
                ORDER BY c.id DESC
                LIMIT %s OFFSET %s
            """
            rows = await self.db.fetch_all(query, tuple(params))
            
            conversations = []
            for cr in rows:
                conversations.append({
                    "id": str(cr[0]),
                    "status": cr[1],
                    "mode": cr[2],
                    "name": str(cr[4]),
                    "phoneNumber": str(cr[5]),
                    "lastMessage": cr[6],
                    "timestamp": cr[7]
                })
                
            return {
                "conversations": conversations,
                "total": total,
                "page": filter.page,
                "limit": filter.limit
            }
        except Exception as e:
            logger.error(f"Error getting organization conversations: {str(e)}", exc_info=True)
            raise

    async def get_organization_contacts(self, org_id: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get organization contacts"""
        try:
            offset = (page - 1) * limit
            
            # 1. Get total count
            count_query = "SELECT COUNT(*) FROM contacts WHERE organization_id = %s"
            count_result = await self.db.fetch_one(count_query, (org_id,))
            total = count_result[0] if count_result else 0
            
            if total == 0:
                return {
                    "contacts": [], # Changed from items to contacts to match ContactsListResponse usually
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    # "pages": 0 # helper
                }

            # 2. Get contacts
            contacts_query = """
                SELECT id, name, phone_number, email, stamps, organization_id, created_at, updated_at, profile_picture
                FROM contacts 
                WHERE organization_id = %s
                LIMIT %s OFFSET %s
            """
            contacts_rows = await self.db.fetch_all(contacts_query, (org_id, limit, offset))
            
            contacts = []
            
            for row in contacts_rows:
                contacts.append({
                    "id": str(row[0]),
                    "name": row[1],
                    "phoneNumber": row[2],
                    "email": row[3],
                    "stamps": str(row[4]) if row[4] is not None else None,
                    "organizationId": str(row[5]),
                    "profilePicture": row[8],
                    "labels": []
                })

            import math
            return {
                "contacts": contacts,
                "total": total,
                "page": page,
                "limit": limit
            }
        except Exception as e:
            logger.error(f"Error getting organization contacts: {str(e)}", exc_info=True)
            raise

    async def get_contact_conversations(self, org_id: str, contact_id: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get conversations for a specific contact in an organization"""
        try:
            # Verify contact belongs to org
            check_query = "SELECT id FROM contacts WHERE id = %s AND organization_id = %s"
            if not await self.db.fetch_one(check_query, (contact_id, org_id)):
                return None

            offset = (page - 1) * limit
            
            count_query = "SELECT COUNT(*) FROM conversations WHERE contact_id = %s"
            count_res = await self.db.fetch_one(count_query, (contact_id,))
            total = count_res[0] if count_res else 0

            query = """
                SELECT id, contact_id, metadata, status, mode
                FROM conversations
                WHERE contact_id = %s
                ORDER BY id DESC
                LIMIT %s OFFSET %s
            """
            rows = await self.db.fetch_all(query, (contact_id, limit, offset))
            
            conversations = []
            for cr in rows:
                conversations.append({
                    "id": str(cr[0]),
                    "contact_id": str(cr[1]),
                    "metadata": cr[2],
                    "status": cr[3],
                    "mode": cr[4] if cr[4] else 'ai'
                })
                
            return {
                "conversations": conversations,
                "total": total,
                "page": page,
                "limit": limit
            }
        except Exception as e:
            logger.error(f"Error getting contact conversations: {str(e)}", exc_info=True)
            raise
    
    async def get_organization_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get organization by email"""
        try:
            query = "SELECT id, name, email, status, phone_id, created_at, updated_at FROM organizations WHERE email = %s"
            result = await self.db.fetch_one(query, (email,))
            
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
            logger.error(f"Error getting organization by email: {str(e)}")
            return None

    async def get_organization_by_id(self, id: str) -> Optional[GetOrganizationResponse]:
        """Get organization by id"""
        try:
            query = "SELECT id, name, email, status, phone_id, created_at, updated_at FROM organizations WHERE id = %s"
            result = await self.db.fetch_one(query, (id,))
            
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
            logger.error(f"Error getting organization by id: {str(e)}")
            return None

    async def get_organization_by_phone_id(self, phone_id: str) -> Optional[GetOrganizationResponse]:
        """Get organization by phone_id"""
        try:
            query = "SELECT id, name, email, status, agent_id FROM organizations WHERE phone_id = %s"
            result = await self.db.fetch_one(query, (phone_id,))
            
            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "email": result[2],
                    "status": result[3],
                    "agent_id": result[4]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting organization by email: {str(e)}")
            return None

    async def create_organization(self, org_data: OrganizationCreate) -> GetOrganizationResponse:
        """Create a new organization"""
        try:
            # Check if email exists
            existing_org = await self.get_organization_by_email(org_data.email)
            if existing_org:
                raise ValueError("Email already registered")

            query = """
                INSERT INTO organizations (name, email, phone_id, agent_id, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            status = 'active'
            
            await self.db.execute(query, (
                org_data.name,
                org_data.email, 
                org_data.phone_id,
                org_data.agent_id,
                status
            ))
            
            # Fetch created org
            org = await self.get_organization_by_email(org_data.email)
            
            return org

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
                    "agent_id": result[5],
                    "created_at": result[6],
                    "updated_at": result[7]
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

    async def get_organization_users(self, org_id: str) -> List[Dict[str, Any]]:
        """Get all users in an organization"""
        try:
            query = """
                SELECT ou.id, ou.user_id, ou.organization_id, ou.role_id, ou.created_at, ou.updated_at,
                       u.name as user_name, u.email as user_email,
                       r.name as role_name
                FROM organization_users ou
                JOIN users u ON ou.user_id = u.id
                JOIN roles r ON ou.role_id = r.id
                WHERE ou.organization_id = %s
            """
            rows = await self.db.fetch_all(query, (org_id,))
            
            return [{
                "id": str(r[0]),
                "user": {
                    "id": str(r[1]),
                    "name": r[6],
                    "email": r[7]
                },
                "organization_id": str(r[2]),
                "role": {
                    "id": str(r[3]),
                    "name": r[8]
                },
                "created_at": r[4],
                "updated_at": r[5]
            } for r in rows]
        except Exception as e:
            logger.error(f"Error getting organization users: {str(e)}", exc_info=True)
            raise

    async def get_organization_phones(self, org_id: str) -> List[str]:
        """Get all phones in an organization"""
        try:
            query = """
                SELECT phone_number
                FROM organization_users ou
                WHERE ou.organization_id = %s
            """
            rows = await self.db.fetch_all(query, (org_id,))
            
            return [r[0] for r in rows]
        except Exception as e:
            logger.error(f"Error getting organization users: {str(e)}", exc_info=True)
            raise

    async def invite_user(self, org_id: str, email: str, role_id: str | None = None) -> Optional[Dict[str, Any]]:
        """Invite existing user to organization"""
        try:
            # Check if user exists
            user_query = "SELECT id FROM users WHERE email = %s"
            user_result = await self.db.fetch_one(user_query, (email,))
            if not user_result:
                raise ValueError("User with this email does not exist")
            
            user_id = user_result[0]
            
            # Check if already added
            check_query = "SELECT id FROM organization_users WHERE organization_id = %s AND user_id = %s"
            if await self.db.fetch_one(check_query, (org_id, user_id)):
                raise ValueError("User is already in this organization")
            
            role_id = role_id if role_id else str(await auth_service.get_role_id("user"))
            if not role_id:
                raise ValueError("User role not found")
                
            # Insert
            query = """
                INSERT INTO organization_users (user_id, organization_id, role_id)
                VALUES (%s, %s, %s)
            """
            await self.db.execute(query, (user_id, org_id, role_id))
            
            # Return added user info
            return await self.get_organization_user(org_id, str(user_id))
            
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Error inviting user: {str(e)}", exc_info=True)
            raise

    async def get_organization_user(self, org_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get single organization user"""
        try:
            query = """
                SELECT ou.id, ou.user_id, ou.organization_id, ou.role_id, ou.created_at, ou.updated_at,
                       u.name as user_name, u.email as user_email,
                       r.name as role_name
                FROM organization_users ou
                JOIN users u ON ou.user_id = u.id
                JOIN roles r ON ou.role_id = r.id
                WHERE ou.organization_id = %s AND ou.user_id = %s
            """
            r = await self.db.fetch_one(query, (org_id, user_id))
            if r:
                return {
                    "id": str(r[0]),
                    "user": {
                        "id": str(r[1]),
                        "name": r[6],
                        "email": r[7]
                    },
                    "organization_id": str(r[2]),
                    "role": {
                        "id": str(r[3]),
                        "name": r[8]
                    },
                    "created_at": r[4],
                    "updated_at": r[5]
                }
            return None
        except Exception as e:
             logger.error(f"Error getting org user: {str(e)}", exc_info=True)
             raise

    async def update_user_role(self, org_id: str, user_id: str, role_id: str) -> Optional[Dict[str, Any]]:
        """Update user role in organization"""
        try:
            query = "UPDATE organization_users SET role_id = %s WHERE organization_id = %s AND user_id = %s"
            await self.db.execute(query, (role_id, org_id, user_id))
            return await self.get_organization_user(org_id, user_id)
        except Exception as e:
            logger.error(f"Error updating org user role: {str(e)}", exc_info=True)
            raise

    async def update_user_phone_number(self, org_id: str, user_id: str, phone_number: str) -> Optional[Dict[str, Any]]:
        """Update user phone number in organization"""
        try:
            query = "UPDATE organization_users SET phone_number = %s WHERE organization_id = %s AND user_id = %s"
            await self.db.execute(query, (phone_number, org_id, user_id))
            return await self.get_organization_user(org_id, user_id)
        except Exception as e:
            logger.error(f"Error updating org user role: {str(e)}", exc_info=True)
            raise

    async def remove_user(self, org_id: str, user_id: str) -> bool:
        """Remove user from organization"""
        try:
            query = "DELETE FROM organization_users WHERE organization_id = %s AND user_id = %s"
            result = await self.db.execute(query, (org_id, user_id))
            return result["affected_rows"] > 0
        except Exception as e:
            logger.error(f"Error removing user from org: {str(e)}", exc_info=True)
            raise

    async def check_is_org_admin(self, org_id: str, user_id: str) -> bool:
        """Check if user is admin of the organization"""
        try:
            query = """
                SELECT r.name 
                FROM organization_users ou
                JOIN roles r ON ou.role_id = r.id
                WHERE ou.organization_id = %s AND ou.user_id = %s
            """
            result = await self.db.fetch_one(query, (org_id, user_id))
            if result and result[0] == 'admin':
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking org admin: {str(e)}")
            return False

    async def check_is_org_member(self, org_id: str, user_id: str) -> bool:
        """Check if user is member of the organization"""
        try:
            query = "SELECT id FROM organization_users WHERE organization_id = %s AND user_id = %s"
            result = await self.db.fetch_one(query, (org_id, user_id))
        except Exception as e:
             logger.error(f"Error checking org member: {str(e)}")
             return False

    async def get_all_organizations(self, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get all organizations (Admin)"""
        try:
            offset = (page - 1) * limit
            
            count_query = "SELECT COUNT(*) FROM organizations"
            count_result = await self.db.fetch_one(count_query)
            total = count_result[0] if count_result else 0
            
            if total == 0:
                 return {
                    "organizations": [],
                    "total": 0,
                    "page": page,
                    "limit": limit
                }

            query = """
                SELECT id, name, email, status, phone_id, agent_id, created_at, updated_at 
                FROM organizations
                LIMIT %s OFFSET %s
            """
            rows = await self.db.fetch_all(query, (limit, offset))
            
            orgs = []
            for r in rows:
                orgs.append({
                    "id": str(r[0]),
                    "name": r[1],
                    "email": r[2],
                    "status": r[3],
                    "phone_id": r[4],
                    "agent_id": r[5],
                    "created_at": r[6],
                    "updated_at": r[7]
                })

            return {
                "organizations": orgs,
                "total": total,
                "page": page,
                "limit": limit
            }
        except Exception as e:
            raise

    async def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all organizations a user belongs to"""
        try:
            query = """
                SELECT o.id, o.name, o.email, o.status, ou.phone_number,
                       r.name as role_name, r.id as role_id
                FROM organization_users ou
                JOIN organizations o ON ou.organization_id = o.id
                JOIN roles r ON ou.role_id = r.id
                WHERE ou.user_id = %s
            """
            rows = await self.db.fetch_all(query, (user_id,))
            
            result = []
            for r in rows:
                result.append({
                    "id": str(r[0]),
                    "name": r[1],
                    "email": r[2],
                    "status": r[3],
                    "organization_user": {
                         "phone_number": r[4],
                         "role": {
                             "id": str(r[6]),
                             "name": r[5]
                         }
                    }
                })
            return result
        except Exception as e:
            logger.error(f"Error getting user organizations: {str(e)}", exc_info=True)
            raise
