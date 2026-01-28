from app.routers.auth import auth_service
from app.models.organization_models import GetOrganizationResponse
import logging
from typing import Optional, Dict, Any, List
from ..database.mysql import MariaDBClient
from ..models.organization_models import (
    OrganizationCreate,
    OrganizationUpdateStatus,
    OrganizationUpdateProfile,
    ConversationFilter,
)

logger = logging.getLogger(__name__)


class OrganizationPermissionService:
    def __init__(self):
        self.db = MariaDBClient()

    async def init_org_permission(self, org_id: str) -> bool:
        """
            Creates initial organization permission: 
            ['admin', 'user']
        """
        