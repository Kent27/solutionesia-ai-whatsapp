from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from ..models.auth_models import UserLogin, UserRegister, UserResponse, AuthResponse, UserNameUpdate
from ..services.auth_service import AuthService
from ..utils.auth_utils import get_current_user
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])
auth_service = AuthService()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

@router.post("/login", response_model=AuthResponse)
async def login(user_data: UserLogin, response: Response) -> Dict[str, Any]:
    """
    Authenticate a user and return a JWT token (in cookie)
    """
    try:
        result = await auth_service.authenticate_user(
            email=user_data.email,
            password=user_data.password
        )
        
        if not result:
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )

        # Set cookie
        response.set_cookie(
            key="access_token",
            value=result["token"],
            httponly=True,
            # secure=True, # Should be true in prod suitable for localhost testing to be auto/loose or conditional
            samesite="lax",
            max_age=60 * 60 * 24 # 24 hours
        )
            
        return {"user": result["user"]}
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error during login: {str(e)}"
        )

@router.post("/register", response_model=AuthResponse)
async def register(user_data: UserRegister, response: Response) -> Dict[str, Any]:
    """
    Register a new user
    """
    try:
        logger.info(f"Registration request received for email: {user_data.email}")
        
        # Check if user already exists
        existing_user = await auth_service.get_user_by_email(user_data.email)
        if existing_user:
            logger.warning(f"Registration failed: User already exists with email {user_data.email}")
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists"
            )
            
        # Create new user
        logger.info(f"Creating new user with email: {user_data.email}")
        result = await auth_service.create_user(
            name=user_data.name,
            email=user_data.email,
            password=user_data.password
        )
        
        if not result:
            logger.error(f"Failed to create user: {user_data.email}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create user"
            )
            
        # Log in the newly created user
        logger.info(f"User created successfully, attempting authentication: {user_data.email}")
        auth_result = await auth_service.authenticate_user(
            email=user_data.email,
            password=user_data.password
        )
        
        if not auth_result:
            logger.error(f"Failed to authenticate newly created user: {user_data.email}")
            raise HTTPException(
                status_code=500,
                detail="Failed to authenticate new user"
            )
            
        # Set cookie
        response.set_cookie(
            key="access_token",
            value=auth_result["token"],
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24
        )

        logger.info(f"User registration completed successfully: {user_data.email}")
        return {"user": auth_result["user"]}
    except HTTPException as he:
        logger.warning(f"HTTP exception during registration: {str(he)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error during registration: {str(e)}"
        )

@router.put("/username", response_model=Dict[str, str])
async def update_username(
    user_data: UserNameUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Update the authenticated user's name
    """
    try:
        user_id = current_user["id"]
        logger.info(f"Update username request for user_id: {user_id}")
        
        result = await auth_service.update_user_name(
            user_id=user_id,
            new_name=user_data.name
        )
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to update user name"
            )
            
        return {"message": "User name updated successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating username: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error updating username: {str(e)}"
        ) 