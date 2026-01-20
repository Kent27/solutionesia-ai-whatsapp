from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from typing import List
from ..models.organization_models import (
    OrganizationCreate, OrganizationResponse, OrganizationLogin, 
    Token, OrganizationUpdateStatus, OrganizationUpdateProfile
)
from ..services.organization_service import OrganizationService
from ..services.organization_auth_service import OrganizationAuthService
import logging
import jwt as pyjwt
import os

router = APIRouter(prefix="/organization", tags=["Organization"])
logger = logging.getLogger(__name__)

org_service = OrganizationService()
auth_service = OrganizationAuthService()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="organization/login")

async def get_current_organization(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = pyjwt.decode(token, auth_service.secret_key, algorithms=[auth_service.algorithm])
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
    except pyjwt.PyJWTError:
        raise credentials_exception
    
    org = await auth_service.get_organization_by_email(email)
    if org is None:
        raise credentials_exception
    return org

@router.post("/register", response_model=OrganizationResponse)
async def register_organization(org_data: OrganizationCreate):
    try:
        org = await org_service.create_organization(org_data)
        if not org:
            raise HTTPException(status_code=400, detail="Organization could not be created")
        return org
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"detail": str(e), "trace": traceback.format_exc()})

@router.post("/login", response_model=Token)
async def login_organization(login_data: OrganizationLogin):
    auth_result = await auth_service.authenticate_organization(login_data.email, login_data.password)
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": auth_result["token"], "token_type": "bearer"}

@router.put("/{org_id}/status", response_model=OrganizationResponse)
async def update_organization_status(org_id: str, status_data: OrganizationUpdateStatus):
    # Unprotected as per user request
    org = await org_service.update_status(org_id, status_data)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.put("/me", response_model=OrganizationResponse)
async def update_organization_profile(
    profile_data: OrganizationUpdateProfile,
    current_org: dict = Depends(get_current_organization)
):
    org_id = current_org['id']
    org = await org_service.update_profile(org_id, profile_data)
    if not org:
        raise HTTPException(status_code=400, detail="Could not update profile")
    return org
