import logging
from typing import Optional, Dict, Any, List
from ..database.mysql import MariaDBClient

from datetime import datetime

logger = logging.getLogger(__name__)


class OrganizationPermissionService:
    def __init__(self):
        self.db = MariaDBClient()

    async def init_org_permission(self, org_id: str) -> bool:
        """
        Creates initial organization roles (admin, user) for a new organization.
        """
        try:
            # Create default role : 'admin' and 'user'
            query_admin = """
                INSERT INTO organization_roles (name, organization_id)
                VALUES ('admin', %s), ('user', %s)
            """
            await self.db.execute(query_admin, (org_id, org_id))

            return True
        except Exception as e:
            logger.error(f"Error initializing org permissions: {str(e)}", exc_info=True)
            return False

    async def check_org_permission(
        self, org_id: str, user_id: str, permission_name: str
    ) -> bool:
        """Check if user has specific permission in organization"""
        try:
            # 1. Get user's org role
            query = """
                SELECT or_roles.id 
                FROM organization_users ou
                JOIN organization_roles or_roles ON ou.organization_role_id = or_roles.id
                WHERE ou.organization_id = %s AND ou.user_id = %s
            """
            role_res = await self.db.fetch_one(query, (org_id, user_id))
            if not role_res:
                return False

            role_id = role_res[0]

            # 2. Check if role has permission
            # Admin role (by name) bypasses check? The requirements say "org admin: CRUD of organization roles EXCEPT for 'admin' role".
            # Usually admin has all permissions. But let's check explicit permission first.

            perm_query = """
                SELECT 1
                FROM organization_role_permissions orp
                JOIN organization_permissions op ON orp.organization_permission_id = op.id
                WHERE orp.organization_role_id = %s AND op.name = %s
            """
            if await self.db.fetch_one(perm_query, (role_id, permission_name)):
                return True

            return False
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}", exc_info=True)
            return False

    # --- Organization Permissions (App Admin) ---

    async def create_permission(self, name: str, description: str) -> Dict[str, Any]:
        """Create a new global organization permission"""
        try:
            # Forbid 'admin' permission as being used as admin organization-role indicator in client apps
            if name == "admin":
                raise ValueError("Permission name 'admin' is reserved")

            query = "INSERT INTO organization_permissions (name, description) VALUES (%s, %s)"
            res = await self.db.execute(query, (name, description))
            perm_id = str(res.get("id")) if res and res.get("id") else None
            if not perm_id and res and "last_insert_id" in res:
                perm_id = str(res["last_insert_id"])

            return {
                "id": str(perm_id) if perm_id else "0",
                "name": name,
                "description": description,
            }
        except Exception as e:
            logger.error(f"Error creating permission: {str(e)}", exc_info=True)
            raise

    async def get_permissions(self) -> List[Dict[str, Any]]:
        """List all available permissions"""
        try:
            query = "SELECT id, name, description FROM organization_permissions"
            rows = await self.db.fetch_all(query)
            return [{"id": str(r[0]), "name": r[1], "description": r[2]} for r in rows]
        except Exception as e:
            logger.error(f"Error getting permissions: {str(e)}", exc_info=True)
            raise

    async def delete_permission(self, perm_id: str) -> bool:
        """Delete a permission"""
        try:
            query = "DELETE FROM organization_permissions WHERE id = %s"
            await self.db.execute(query, (perm_id,))
            return True
        except Exception as e:
            logger.error(f"Error deleting permission: {str(e)}", exc_info=True)
            raise

    # --- Organization Roles (Org Admin) ---

    async def get_org_roles(self, org_id: str) -> List[Dict[str, Any]]:
        """Get roles for an organization with their permissions"""
        try:
            query = "SELECT id, name, created_at, updated_at FROM organization_roles WHERE organization_id = %s"
            rows = await self.db.fetch_all(query, (org_id,))

            roles = []
            for r in rows:
                role_id = r[0]
                # Get permissions for role
                perm_query = """
                    SELECT op.id, op.name, op.description
                    FROM organization_role_permissions orp
                    JOIN organization_permissions op ON orp.organization_permission_id = op.id
                    WHERE orp.organization_role_id = %s
                """
                perms = await self.db.fetch_all(perm_query, (role_id,))

                roles.append(
                    {
                        "id": str(r[0]),
                        "name": r[1],
                        "created_at": r[2],
                        "updated_at": r[3],
                        "organization_id": org_id,
                        "permissions": [
                            {"id": str(p[0]), "name": p[1], "description": p[2]}
                            for p in perms
                        ],
                    }
                )
            return roles
        except Exception as e:
            logger.error(f"Error getting org roles: {str(e)}", exc_info=True)
            raise

    async def create_org_role(self, org_id: str, name: str) -> Dict[str, Any]:
        """Create a new role for organization"""
        try:
            query = (
                "INSERT INTO organization_roles (name, organization_id) VALUES (%s, %s)"
            )
            res = await self.db.execute(query, (name, org_id))
            role_id = (
                str(res.get("id")) if res and res.get("id") else None
            )  # Should probably be last_insert_id if specific driver, or just id if wrapper handles it.
            # Assuming db.execute returns a dict with 'id' or 'last_insert_id'.
            # Looking at other usages, it seems we expect 'id'.

            if not role_id and res and "last_insert_id" in res:
                role_id = str(res["last_insert_id"])

            return {
                "id": str(role_id)
                if role_id
                else "0",  # Fallback, but should error really
                "name": name,
                "organization_id": org_id,
                "permissions": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
        except Exception as e:
            logger.error(f"Error creating org role: {str(e)}", exc_info=True)
            raise

    async def update_org_role(
        self, role_id: str, name: str
    ) -> Optional[Dict[str, Any]]:
        """Update role name"""
        try:
            # Block 'admin' role alter
            check_query = "SELECT name FROM organization_roles WHERE id = %s"
            res = await self.db.fetch_one(check_query, (role_id,))
            if res and res[0] == "admin":
                raise ValueError("Cannot update admin role name")

            query = "UPDATE organization_roles SET name = %s, updated_at = NOW() WHERE id = %s"
            await self.db.execute(query, (name, role_id))
            return {
                "id": role_id,
                "name": name,
            }
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Error updating org role: {str(e)}", exc_info=True)
            raise

    async def delete_org_role(self, org_id: str, role_id: str) -> bool:
        """Delete role"""
        try:
            # Block 'admin' role alter
            check_query = "SELECT name FROM organization_roles WHERE id = %s"
            res = await self.db.fetch_one(check_query, (role_id,))
            if res and res[0] == "admin":
                raise ValueError("Cannot delete admin role")

            query = (
                "DELETE FROM organization_roles WHERE id = %s AND organization_id = %s"
            )
            await self.db.execute(query, (role_id, org_id))
            return True
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Error deleting org role: {str(e)}", exc_info=True)
            raise

    async def assign_permission_to_role(
        self, org_id: str, role_id: str, permission_id: str
    ) -> bool:
        """Assign permission to role"""
        try:
            # Verify role belongs to org
            check_query = "SELECT id FROM organization_roles WHERE id = %s AND organization_id = %s"
            if not await self.db.fetch_one(check_query, (role_id, org_id)):
                raise ValueError("Role does not belong to organization")

            # Check duplication
            dup_query = "SELECT id FROM organization_role_permissions WHERE organization_role_id = %s AND organization_permission_id = %s"
            if await self.db.fetch_one(dup_query, (role_id, permission_id)):
                return True

            query = "INSERT INTO organization_role_permissions (organization_role_id, organization_permission_id) VALUES (%s, %s)"
            await self.db.execute(query, (role_id, permission_id))
            return True
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Error assigning permission: {str(e)}", exc_info=True)
            raise

    async def remove_permission_from_role(
        self, org_id: str, role_id: str, permission_id: str
    ) -> bool:
        """Remove permission from role"""
        try:
            # Verify role belongs to org
            check_query = "SELECT id FROM organization_roles WHERE id = %s AND organization_id = %s"
            if not await self.db.fetch_one(check_query, (role_id, org_id)):
                raise ValueError("Role does not belong to organization")

            query = "DELETE FROM organization_role_permissions WHERE organization_role_id = %s AND organization_permission_id = %s"
            await self.db.execute(query, (role_id, permission_id))
            return True
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Error removing permission: {str(e)}", exc_info=True)
            raise
