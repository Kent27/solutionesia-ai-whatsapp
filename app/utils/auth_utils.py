from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any
import jwt as pyjwt
import os
import logging

from ..database.mysql import MariaDBClient

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get the current authenticated user from the token (cookie or header)"""
    try:
        # Try to get token from cookie
        token = request.cookies.get("access_token")
        logger.info(token)
        
        # Fallback to Authorization header
        # if not token:
        #     auth_header = request.headers.get("Authorization")
        #     if auth_header and auth_header.startswith("Bearer "):
        #         token = auth_header.split(" ")[1]

        if not token:
             raise HTTPException(status_code=401, detail="Not authenticated")

        # Decode the JWT token
        payload = pyjwt.decode(
            token, 
            os.getenv("JWT_SECRET_KEY", "your-secret-key"), 
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
            
        return {"id": user_id, "email": payload.get("email")}
    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

async def get_current_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Check if the current user has 'admin' role.
    This requires a database lookup since the role might not be in the token 
    or we want to ensure it's up to date.
    """
    db = MariaDBClient()
    try:
        user_id = current_user["id"]
        
        # Query to get the role name for the user
        query = """
            SELECT r.name 
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = %s
        """
        
        result = await db.fetch_one(query, (user_id,))
        
        if not result:
            # User might not found or has no role assigned
            logger.warning(f"User {user_id} has no role or does not exist")
            raise HTTPException(status_code=403, detail="Not authorized")
            
        role_name = result[0]
        
        if role_name != 'admin':
            logger.warning(f"User {user_id} attempted admin action with role {role_name}")
            raise HTTPException(status_code=403, detail="Unauthorized")
            
        return current_user
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error verifying admin role: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during authorization")
    finally:
        await db.close() 