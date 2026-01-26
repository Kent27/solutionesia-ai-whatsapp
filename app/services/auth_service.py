from app.models.auth_models import AuthUserResponse
from app.models.auth_models import UserResponse
from app.models.user_models import UserListFilter
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

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Get user by email"""
        try:
            query = "SELECT id, name, email, profile_picture FROM users WHERE email = %s"
            result = await self.db.fetch_one(query, (email,))
            
            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "email": result[2],
                    "profile_picture": result[3]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
            
    async def get_user_with_role(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details with role by ID"""
        try:
            query = """
                SELECT u.id, u.name, u.email, u.profile_picture, r.name as role_name 
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.id
                WHERE u.id = %s
            """
            result = await self.db.fetch_one(query, (user_id,))
            
            if result:
                return {
                    "id": str(result[0]),
                    "name": result[1],
                    "email": result[2],
                    "profile_picture": result[3],
                    "role": result[4] if result[4] else "user"
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user with role: {str(e)}")
            return None
            
    async def get_auth_user_by_email(self, email: str) -> Optional[AuthUserResponse]:
        """Get auth user by email"""
        try:
            query = "SELECT id, name, email, password FROM users WHERE email = %s"
            result = await self.db.fetch_one(query, (email,))
            
            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "email": result[2],
                    "password": result[3]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None

    async def get_role_id(self, role: str) -> Optional[int]:
        """Get role ID by role name"""
        try:
            query = "SELECT id FROM roles WHERE name = %s"
            result = await self.db.fetch_one(query, (role,))
            
            if result:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Error getting role ID: {str(e)}")
            return None

    async def create_user(self, name: str, email: str, password: str, role: str = 'user') -> UserResponse:
        """Create a new user"""
        try:
            logger.info(f"Starting user creation for email: {email}")
            hashed_password = self._get_password_hash(password)
            role_id = await self.get_role_id(role)

            # Insert the user
            query = """
                INSERT INTO users (name, email, password, role_id)
                VALUES (%s, %s, %s, %s)
            """
            
            try:
                await self.db.execute(query, (name, email, hashed_password, role_id))
            except Exception as e:
                # Check if the error is due to duplicate email
                if "Duplicate entry" in str(e) and "email" in str(e):
                    logger.warning(f"Attempted to create user with existing email: {email}")
                    raise ValueError("User with this email already exists")
                raise
            
            logger.info(f"Successfully created user {email}")
            return {
                "name": name,
                "email": email
            }
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            raise  # Re-raise the exception to let FastAPI handle it

    async def authenticate_user(self, email: str, password: str) -> AuthUserResponse:
        """Authenticate user and return token"""
        try:
            user = await self.get_auth_user_by_email(email)
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
                "id": str(user["id"]),
                "name": user["name"],
                "email": user["email"]
            }
            
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

    async def get_all_users(self, filter: UserListFilter) -> Dict[str, Any]:
        """Get all users with filter"""
        try:
            params = []
            conditions = []
            
            # Base query parts
            base_query = """
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.id
            """
            
            if filter.role:
                conditions.append("r.name = %s")
                params.append(filter.role)
            
            if filter.search:
                search_term = f"%{filter.search}%"
                conditions.append("(u.name LIKE %s OR u.email LIKE %s)")
                params.append(search_term)
                params.append(search_term)
            
            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
                
            # Count
            count_query = f"SELECT COUNT(*) {base_query} {where_clause}"
            count_result = await self.db.fetch_one(count_query, tuple(params))
            total = count_result[0] if count_result else 0
            
            if total == 0:
                return {
                    "users": [],
                    "total": 0,
                    "page": filter.page,
                    "limit": filter.limit
                }

            # Fetch
            offset = (filter.page - 1) * filter.limit
            params.append(filter.limit)
            params.append(offset)
            
            query = f"""
                SELECT u.id, u.name, u.email, u.profile_picture, r.name as role_name
                {base_query}
                {where_clause}
                ORDER BY u.created_at DESC
                LIMIT %s OFFSET %s
            """
            
            rows = await self.db.fetch_all(query, tuple(params))
            
            users = []
            for r in rows:
                users.append({
                    "id": str(r[0]),
                    "name": r[1],
                    "email": r[2],
                    "profile_picture": r[3],
                    "role": r[4] if r[4] else "user"
                })
                
            return {
                "users": users,
                "total": total,
                "page": filter.page,
                "limit": filter.limit
            }
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}", exc_info=True)
            raise 