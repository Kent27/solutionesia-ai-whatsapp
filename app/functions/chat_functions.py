from app.services.conversation_service import update_conversation_mode
from app.services.whatsapp_service import WhatsAppService
import logging
from typing import Dict, Any
from ..utils.google_sheets import set_chat_status
from ..functions.alert_functions import alert_admin

logger = logging.getLogger(__name__)

async def enable_live_chat(phone_number: str, organization_id: str, conversation_id: str) -> Dict[str, Any]:
    """
    Enable Live Chat mode for a customer
    
    Args:
        phone_number: The customer's phone number
        
    Returns:
        Dict: Status and message
    """
    try:
        logger.info('[Entering enable live chat mode]')
        logger.info(phone_number)
        logger.info(organization_id)
        logger.info(conversation_id)

        # Normalize phone number format
        phone_number = phone_number.strip()
        if not phone_number.startswith("+"):
            # Add + if not present for international format
            if phone_number.startswith("62"):
                phone_number = "+" + phone_number
            elif phone_number.startswith("0"):
                # Convert local format to international
                phone_number = "+62" + phone_number[1:]
        if conversation_id:
            # Update conversation mode to "human"
            success = await update_conversation_mode(conversation_id, "human")
        else:
            # Alert admin for live chat request
            success = await alert_admin(
                message=f"Customer asks for Live Chat",
                severity="info",
                context={
                    "phone_number": phone_number,
                    "action": "Live Chat",
                    "status": "Active",
                }
            )
            
        logger.info(success)

        if success:
            logger.info(f"Live Chat mode enabled for {phone_number}")
            
            return {
                "status": "success",
                "message": "Live Chat mode has been enabled. Your messages will now be handled by a human agent."
            }
        else:
            logger.error(f"Failed to enable Live Chat mode for {phone_number} - customer not found")
            return {
                "status": "error",
                "message": "Failed to enable Live Chat mode. Customer not found."
            }
    except Exception as e:
        logger.error(f"Error enabling Live Chat mode: {str(e)}")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }

async def disable_live_chat(phone_number: str) -> Dict[str, Any]:
    """
    Disable Live Chat mode for a customer
    
    Args:
        phone_number: The customer's phone number
        
    Returns:
        Dict: Status and message
    """
    try:
        # Normalize phone number format
        phone_number = phone_number.strip()
        
        success = await set_chat_status(phone_number, "")  # Empty string to disable Live Chat
        
        if success:
            logger.info(f"Live Chat mode disabled for {phone_number}")
            return {
                "status": "success",
                "message": "Live Chat mode has been disabled. Your messages will now be handled by the AI assistant."
            }
        else:
            logger.error(f"Failed to disable Live Chat mode for {phone_number} - customer not found")
            return {
                "status": "error",
                "message": "Failed to disable Live Chat mode. Customer not found."
            }
    except Exception as e:
        logger.error(f"Error disabling Live Chat mode: {str(e)}")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        } 