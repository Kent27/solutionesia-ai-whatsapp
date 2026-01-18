
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request
import os
from .routers import assistant_router, whatsapp, auth, message, contact, label, whatsapp_api, document
from .utils.app_logger import app_logger, log_request, setup_app_logger
import datetime
from fastapi.middleware.cors import CORSMiddleware
import logging

# Set up logging
setup_app_logger()
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Solutionesia AI WhatsApp API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(assistant_router.router)
app.include_router(whatsapp.router)
app.include_router(auth.router)
app.include_router(message.router)
app.include_router(contact.router)
app.include_router(label.router)
app.include_router(whatsapp_api.router)
app.include_router(document.router)

# Configure logging middleware
@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    # Get request body
    body_bytes = await request.body()
    body = body_bytes.decode(errors='replace')
    
    # Process the request
    response = await call_next(request)
    
    # Log the request details
    log_request(
        method=request.method,
        url=str(request.url),
        body=body,
        status_code=response.status_code
    )
    
    return response

# Log application startup
HOST_URL = os.getenv("HOST_URL", "http://localhost")
PORT = os.getenv("PORT", "8000")
IS_PRODUCTION = HOST_URL.startswith("https://") or os.getenv("PRODUCTION", "false").lower() == "true"
FULL_HOST_URL = f"{HOST_URL}:{PORT}" if not IS_PRODUCTION and PORT else HOST_URL
app_logger.info(f"Application starting up. Host URL: {FULL_HOST_URL}")

@app.get("/")
async def root():
    return {"message": "Solutionesia AI WhatsApp API is running"}