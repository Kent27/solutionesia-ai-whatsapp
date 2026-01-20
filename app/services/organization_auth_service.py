import os
import jwt as pyjwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from ..database.mysql import MariaDBClient
import logging
from ..models.organization_models import TokenData

logger = logging.getLogger(__name__)

class OrganizationAuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.db = MariaDBClient()
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24 hours

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = pyjwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    async def get_organization_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get organization by email"""
        try:
            query = "SELECT id, name, email, password, status, phone_id, created_at, updated_at FROM organizations WHERE email = %s"
            result = await self.db.fetch_one(query, (email,))
            
            if result:
                return {
                    "id": str(result[0]),
                    "name": result[1],
                    "email": result[2],
                    "password": result[3],
                    "status": result[4],
                    "phone_id": result[5],
                    "created_at": result[6],
                    "updated_at": result[7]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting organization by email: {str(e)}")
            return None

    async def authenticate_organization(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate organization and return token"""
        try:
            org = await self.get_organization_by_email(email)
            if not org:
                return None
                
            if not self.verify_password(password, org["password"]):
                return None
            
            # Check if organization is active (optional, but good practice, though user only asked for status update capability, not necessarily blocking login based on it, but usually inactive orgs shouldn't login. I'll stick to basic auth for now as per minimal requirements)

            # Create access token
            token_data = {
                "sub": str(org["id"]),
                "email": org["email"],
                "role": "organization" # Distinguish from user tokens if needed
            }
            token = self.create_access_token(token_data)
            
            return {
                "organization": {
                    "id": str(org["id"]),
                    "name": org["name"],
                    "email": org["email"],
                    "status": org["status"],
                    "phone_id": org["phone_id"]
                },
                "token": token
            }
        except Exception as e:
            logger.error(f"Error authenticating organization: {str(e)}", exc_info=True)
            return None
