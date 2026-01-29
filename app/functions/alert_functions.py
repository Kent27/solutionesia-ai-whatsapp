import os
import logging
from typing import Dict, Any
from ..services.whatsapp_service import WhatsAppService
from datetime import datetime
from ..services.organization_service import OrganizationService

logger = logging.getLogger(__name__)
whatsapp_service = WhatsAppService()

async def alert_admin(message: str, organization_id: str, context: Dict[str, Any], severity: str = "info") -> Dict[str, Any]:
    """
    Send an alert message to the admin's WhatsApp number

    Args:
        message: The alert message to send
        severity: Alert severity level (info, warning, error, critical)
        context: Additional context information to include in the alert
        organization_id: Organization ID
    Returns:
        Dict: Status and message
    """
    try:
        # Format the alert message with timestamp and severity
        logger.info(f"Sending alert to admin: {message}, {organization_id}, {context}, {severity}")
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"🚨 *ALERT* [{severity.upper()}] 🚨\n\n"
        formatted_message += f"*Time:* {timestamp}\n\n"
        formatted_message += f"*Message:* {message}\n"
        
        # Add context information if provided
        if context:
            formatted_message += "\n*Context:*\n"
            for key, value in context.items():
                formatted_message += f"- {key}: {value}\n"
        
        # Add severity-specific emoji
        if severity.lower() == "warning":
            formatted_message = "⚠️ " + formatted_message
        elif severity.lower() == "error":
            formatted_message = "❌ " + formatted_message
        elif severity.lower() == "critical":
            formatted_message = "🔥 " + formatted_message
        else:  # info
            formatted_message = "ℹ️ " + formatted_message
        
        org_service = OrganizationService()
        org = await org_service.get_organization_by_id(organization_id)

        if not org or not org.phone_id:
            logger.error(f"Organization not found: {organization_id}")
            return {
                "status": "error",
                "message": "Organization not found"
            }

        org_phones = await org_service.get_organization_phones_with_takeover_permission(
            organization_id
        )

        logger.info(f"Sending alert to {len(org_phones)} admins: {str(org_phones)}")

        for phone_num in org_phones:
            # Send the message via WhatsApp
            await whatsapp_service.send_message(
                to=phone_num,
                message=formatted_message,
                phone_id=org.phone_id
            )
        
        return {
            "status": "success",
            "message": "Alert sent to admin successfully",
            "details": {
                "admin_phone": str(org_phones),
                "severity": severity,
                "timestamp": timestamp,
            },
        }
    except Exception as e:
        logger.error(f"Error sending admin alert: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to send alert: {str(e)}"
        } 