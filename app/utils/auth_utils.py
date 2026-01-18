from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any
import jwt as pyjwt
import os
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get the current authenticated user from the token"""
    try:
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