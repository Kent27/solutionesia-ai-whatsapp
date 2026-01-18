import os
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class WhatsAppAPIService:
    def __init__(self):
        self.api_version = "v24.0"
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.admin_phone = os.getenv("ADMIN_WHATSAPP_NUMBER")
        
        if not all([self.phone_number_id, self.access_token]):
            logger.error("Missing required WhatsApp environment variables")
            raise ValueError("Missing required WhatsApp environment variables")
    
    async def get_contact_info(self, phone_number: str) -> Dict[str, Any]:
        """
        Get contact information from WhatsApp API
        
        Args:
            phone_number: The phone number to get information for
            
        Returns:
            Contact information or error details
        """
        try:
            # Normalize phone number format (ensure it has + prefix)
            if not phone_number.startswith("+"):
                phone_number = f"+{phone_number}"
            
            # Build the API endpoint
            url = f"{self.base_url}/{self.phone_number_id}/contacts"
            
            # Query parameters
            params = {
                "access_token": self.access_token,
                "phone_number": phone_number
            }
            
            # Make the API request
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                
                response_data = response.json()
                logger.debug(f"Contact API response: {response_data}")
                
                if response.status_code != 200:
                    logger.error(f"Error fetching WhatsApp contact info: {response.text}")
                    return {
                        "success": False,
                        "error_message": response_data.get("error", {}).get("message", "Unknown error")
                    }
                
                # Process the contact data
                contact_data = response_data.get("data", [{}])[0] if response_data.get("data") else {}
                
                # Convert timestamp to readable format if available
                last_active = contact_data.get("last_active_timestamp")
                readable_last_active = None
                if last_active:
                    try:
                        readable_last_active = datetime.fromtimestamp(int(last_active)).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                # Format the contact information
                contact_info = {
                    "wa_id": contact_data.get("wa_id", ""),
                    "profile": contact_data.get("profile", {}),
                    "name": contact_data.get("profile", {}).get("name", ""),
                    "phone_number": phone_number,
                    "status": contact_data.get("status", ""),
                    "about": contact_data.get("about", ""),
                    "email": contact_data.get("email", ""),
                    "last_active_timestamp": last_active,
                    "readable_last_active": readable_last_active,
                    "whatsapp_business_account_id": contact_data.get("whatsapp_business_account_id", "")
                }
                
                return {
                    "success": True,
                    "contact": contact_info
                }
                
        except Exception as e:
            logger.error(f"Error fetching WhatsApp contact info: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error_message": str(e)
            }
    
    async def get_conversation_history(self, phone_number: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch conversation history directly from WhatsApp API
        
        Args:
            phone_number: The phone number to get conversation history for
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of messages with their metadata
        """
        try:
            # Normalize phone number format (ensure it has + prefix)
            if not phone_number.startswith("+"):
                phone_number = f"+{phone_number}"
            
            # Build the API endpoint
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            
            # Query parameters
            params = {
                "access_token": self.access_token,
                "limit": limit,
                "phone_number": phone_number
            }
            
            # Make the API request
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Error fetching WhatsApp conversation history: {response.text}")
                    return []
                
                data = response.json()
                messages = []
                
                # Process and format the messages
                for msg in data.get("data", []):
                    formatted_msg = self._format_message(msg)
                    if formatted_msg:
                        messages.append(formatted_msg)
                
                return messages
                
        except Exception as e:
            logger.error(f"Error fetching WhatsApp conversation history: {str(e)}", exc_info=True)
            return []
    
    async def get_media_url(self, media_id: str) -> Optional[str]:
        """
        Get the URL for a media attachment
        
        Args:
            media_id: The WhatsApp media ID
            
        Returns:
            URL to the media file or None if not found
        """
        try:
            url = f"{self.base_url}/{media_id}"
            
            params = {
                "access_token": self.access_token
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Error fetching media URL: {response.text}")
                    return None
                
                data = response.json()
                return data.get("url")
                
        except Exception as e:
            logger.error(f"Error fetching media URL: {str(e)}", exc_info=True)
            return None
    
    def _format_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Format a raw WhatsApp API message into a standardized format
        
        Args:
            msg: Raw message from WhatsApp API
            
        Returns:
            Formatted message or None if the format is not supported
        """
        try:
            message_type = msg.get("type")
            timestamp = msg.get("timestamp")
            
            # Convert timestamp to readable format
            readable_time = None
            if timestamp:
                try:
                    readable_time = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            base_msg = {
                "id": msg.get("id"),
                "timestamp": timestamp,
                "readable_time": readable_time,
                "status": msg.get("status"),
                "type": message_type,
                "from": msg.get("from") or "business_account",
                "to": msg.get("to")
            }
            
            # Add message content based on type
            if message_type == "text":
                base_msg["content"] = msg.get("text", {}).get("body", "")
            elif message_type == "image":
                base_msg["media_id"] = msg.get("image", {}).get("id")
                base_msg["caption"] = msg.get("image", {}).get("caption", "")
            elif message_type == "audio":
                base_msg["media_id"] = msg.get("audio", {}).get("id")
            elif message_type == "video":
                base_msg["media_id"] = msg.get("video", {}).get("id")
                base_msg["caption"] = msg.get("video", {}).get("caption", "")
            elif message_type == "document":
                base_msg["media_id"] = msg.get("document", {}).get("id")
                base_msg["filename"] = msg.get("document", {}).get("filename", "")
            elif message_type == "location":
                location = msg.get("location", {})
                base_msg["latitude"] = location.get("latitude")
                base_msg["longitude"] = location.get("longitude")
                base_msg["name"] = location.get("name", "")
                base_msg["address"] = location.get("address", "")
            else:
                # Skip unsupported message types
                return None
            
            # Determine if message is inbound or outbound
            base_msg["direction"] = "inbound" if base_msg["from"] != "business_account" else "outbound"
            
            return base_msg
            
        except Exception as e:
            logger.error(f"Error formatting message: {str(e)}", exc_info=True)
            return None 