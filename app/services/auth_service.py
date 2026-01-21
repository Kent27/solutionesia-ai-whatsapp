import os
import jwt as pyjwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from ..database.mysql import MariaDBClient
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.db = MariaDBClient()
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24 hours

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def _get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)

    def _create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = pyjwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            query = "SELECT id, name, email, password, profile_picture FROM users WHERE email = %s"
            result = await self.db.fetch_one(query, (email,))
            
            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "email": result[2],
                    "password": result[3],
                    "profile_picture": result[4]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None

    async def create_user(self, name: str, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            logger.info(f"Starting user creation for email: {email}")
            hashed_password = self._get_password_hash(password)
            
            # Insert the user
            query = """
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
            """
            
            try:
                await self.db.execute(query, (name, email, hashed_password))
            except Exception as e:
                # Check if the error is due to duplicate email
                if "Duplicate entry" in str(e) and "email" in str(e):
                    logger.warning(f"Attempted to create user with existing email: {email}")
                    return None
                raise
            
            # Fetch the user by email to return complete data
            logger.info(f"Fetching user data for {email} after insert")
            user = await self.get_user_by_email(email)
            
            if user:
                logger.info(f"Successfully retrieved user data for {email}")
                return {
                    "id": str(user["id"]),
                    "name": user["name"],
                    "email": user["email"],
                    "profile_picture": user["profile_picture"]
                }
            else:
                logger.error(f"Failed to retrieve user data after creation for {email}")
                
            return None
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            raise  # Re-raise the exception to let FastAPI handle it

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return token"""
        try:
            user = await self.get_user_by_email(email)
            if not user:
                return None
                
            if not self._verify_password(password, user["password"]):
                return None
                
            # Create access token
            token_data = {
                "sub": str(user["id"]),
                "email": user["email"]
            }
            token = self._create_access_token(token_data)
            
            # Ensure all user data has proper types
            user_response = {
                "id": str(user["id"]),  # Explicitly convert to string
                "name": user["name"],
                "email": user["email"],
                "profile_picture": user["profile_picture"]
            }
            
            logger.debug(f"User response data: {user_response}")
            
            return {
                "user": user_response,
                "token": token
            }
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}", exc_info=True)
            return None

    async def update_user_name(self, user_id: str, new_name: str) -> bool:
        """Update user's name"""
        try:
            logger.info(f"Updating user name for user_id: {user_id}")
            query = "UPDATE users SET name = %s WHERE id = %s"
            await self.db.execute(query, (new_name, user_id))
            logger.info(f"Successfully updated user name for user_id: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating user name: {str(e)}", exc_info=True)
            return False 