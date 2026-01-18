import base64
import json
import os
import httpx
from PIL import Image  # Change this line
from io import BytesIO
from typing import Dict, Any, List, Optional
import logging
from ..models.whatsapp_models import WhatsAppWebhookRequest, WhatsAppMessage, WhatsAppContact
from ..services.openai_service import OpenAIAssistantService
from ..models.assistant_models import ChatRequest, ChatMessage, ContentItem, ImageFileContent, TextContent
from ..utils.google_sheets import check_customer_exists, update_customer, insert_customer, update_thread_id
from ..utils.logging_utils import log_whatsapp_message
from ..database.mysql import MariaDBClient
import asyncio
from datetime import datetime, timedelta
from collections import OrderedDict

# Replace the existing logger with our app logger
from ..utils.app_logger import app_logger as logger

# Message deduplication cache with a max size to prevent memory leaks
class MessageCache:
    def __init__(self, max_size=1000):
        self.cache = OrderedDict()
        self.max_size = max_size
        
    def add(self, message_id: str) -> bool:
        """
        Add a message ID to the cache.
        Returns True if the message is new, False if it already exists.
        """
        if message_id in self.cache:
            # Update position in OrderedDict (mark as recently used)
            self.cache.move_to_end(message_id)
            return False
            
        # Add new message ID
        self.cache[message_id] = datetime.now()
        
        # Remove oldest entries if cache exceeds max size
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
            
        return True
        
    def cleanup(self, max_age_minutes=30):
        """Remove entries older than max_age_minutes"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=max_age_minutes)
        
        # Create a list of keys to remove (can't modify during iteration)
        to_remove = [
            key for key, timestamp in self.cache.items() 
            if timestamp < cutoff
        ]
        
        # Remove old entries
        for key in to_remove:
            del self.cache[key]

class WhatsAppService:
    def __init__(self):
        self.api_version = "v24.0"
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.assistant_service = OpenAIAssistantService()
        self.openai_headers = {
            "OpenAI-Beta": "assistants=v2",
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
        }
        self.base_openai_url = "https://api.openai.com/v1"
        
        # Initialize database client
        self.db = MariaDBClient()

        # Initialize message cache for deduplication
        self.message_cache = MessageCache()

        if not all([self.phone_number_id, self.access_token]):
            raise ValueError("Missing required WhatsApp environment variables")
        
    async def verify_webhook(self, mode: str, token: str, challenge: str) -> int:
        """Verify WhatsApp webhook"""
        verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        if mode == "subscribe" and token == verify_token:
            return int(challenge)
        raise ValueError("Invalid verification token")

    async def upload_file(self, image_data: bytes, filename: str) -> dict:
        """Upload file to OpenAI for vision processing"""
        url = f"{self.base_openai_url}/files"
        
        try:
            # Create file object from bytes
            files = {
                'file': (filename, image_data, 'image/jpeg'),
                'purpose': (None, 'vision')
            }
            
            async with httpx.AsyncClient() as client:
                # Upload file
                response = await client.post(
                    url, 
                    headers=self.openai_headers,
                    files=files
                )
                
                if response.status_code != 200:
                    raise ValueError(f"Failed to upload file: {response.text}")
                
                file_data = response.json()
                
                # Verify file status
                file_id = file_data.get('id')
                if not file_id:
                    raise ValueError("No file ID in response")
                
                # Wait for file to be processed
                max_retries = 3
                retry_delay = 1  # seconds
                
                for _ in range(max_retries):
                    status_response = await client.get(
                        f"{url}/{file_id}",
                        headers=self.openai_headers
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data.get('status') == 'processed':
                            logger.info(f"File {filename} uploaded and processed successfully")
                            return file_data
                    
                    await asyncio.sleep(retry_delay)
                
                raise ValueError("File upload verification timed out")
                
        except Exception as e:
            raise

    async def process_webhook(self, request: WhatsAppWebhookRequest) -> Dict[str, Any]:
        try:
            entry = request.entry[0]
            change = entry.changes[0]
            value = change.value

            # Check if this is a status update and the value is not None
            if hasattr(value, 'statuses') and value.statuses is not None:
                # Log status update
                if hasattr(value.statuses[0], 'recipient_id'):
                    log_whatsapp_message(
                        phone_number=value.statuses[0].recipient_id,
                        message_type="status",
                        message_data={"status": value.statuses[0].status},
                        direction="outgoing"
                    )
                # Just acknowledge status updates without processing
                return {"status": "success", "message": "Status update received"}

            # Continue only if it's a message
            if not hasattr(value, 'messages') or not value.messages:
                return {"status": "success", "message": "No messages to process"}

            messages = [WhatsAppMessage.model_validate(msg) for msg in value.messages]
            contact = WhatsAppContact.model_validate(value.contacts[0])
            
            # Validate message timestamp (accounting for GMT+7)
            try:
                current_time = int(datetime.now().timestamp())
                message_time = int(messages[0].timestamp)
                time_difference = abs(current_time - message_time)
                
                # Calculate human-readable times for logging
                current_time_readable = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')
                message_time_readable = datetime.fromtimestamp(message_time).strftime('%Y-%m-%d %H:%M:%S')
                
                # Reject messages with timestamps more than 24 hours off
                if time_difference > 86400:  # 24 hours in seconds
                    logger.warning(
                        f"Suspicious timestamp detected! Message: {message_time} ({message_time_readable}), "
                        f"Current: {current_time} ({current_time_readable}), "
                        f"Difference: {time_difference}s ({time_difference/3600:.2f} hours)"
                    )
                    
                    # Log the full webhook payload for suspicious messages
                    logger.warning(f"Suspicious webhook payload: {json.dumps(request.model_dump(), default=str)}")
                    
                    return {
                        "status": "success", 
                        "message": "Message with invalid timestamp rejected",
                        "details": {
                            "message_time": message_time_readable,
                            "current_time": current_time_readable,
                            "time_difference_hours": time_difference/3600
                        }
                    }
            except Exception as e:
                log_whatsapp_message(
                    phone_number=messages[0].from_,
                    message_type="error",
                    message_data={"error": f"Error validating message timestamp: {str(e)}"},
                    direction="system"
                )
                # Continue processing even if timestamp validation fails
            
            # Check for duplicate messages to prevent double processing
            # Use the first message's ID as the key for deduplication
            message_id = messages[0].id
            if not self.message_cache.add(message_id):
                logger.info(f"Skipping duplicate message: {message_id}")
                return {"status": "success", "message": "Duplicate message skipped"}
            # Periodically clean up old message IDs
            if datetime.now().minute % 5 == 0:  # Clean up every 5 minutes
                self.message_cache.cleanup()
            
            # Log each incoming message with enhanced details
            for message in messages:
                log_data = {
                    "message_id": message.id,
                    "timestamp": message.timestamp,
                    "timestamp_readable": datetime.fromtimestamp(int(message.timestamp)).strftime('%Y-%m-%d %H:%M:%S'),
                    "contact_name": contact.profile.name,
                }
                
                if message.type == "text" and hasattr(message, 'text'):
                    log_data["text"] = message.text.body
                elif message.type == "image" and hasattr(message, 'image'):
                    log_data["image_id"] = message.image.id
                    if hasattr(message.image, 'caption') and message.image.caption:
                        log_data["caption"] = message.image.caption
                
                log_whatsapp_message(
                    phone_number=message.from_,
                    message_type=message.type,
                    message_data=log_data,
                    direction="incoming"
                )
            
            # Check if customer exists in Google Sheets - MOVED TO BEGINNING
            customer = await check_customer_exists(messages[0].from_)
            
            # Create customer if they don't exist - MOVED FROM AFTER OPENAI CALL
            if not customer:
                logger.info(f"Customer Does Not Exist - Creating new customer record for: {contact.profile.name} ({messages[0].from_})")
                # For new customers, we need to insert the full record with a temporary thread_id
                # We'll update the thread_id after the OpenAI call
                customer_data = {
                    'phone': messages[0].from_,
                    'name': contact.profile.name,
                    'thread_id': ''  # Empty thread_id will be updated after OpenAI call
                }
                await insert_customer(customer_data)
                
                # Fetch the newly created customer record
                customer = await check_customer_exists(messages[0].from_)
                if not customer:
                    log_whatsapp_message(
                        phone_number=messages[0].from_,
                        message_type="error",
                        message_data={"error": f"Failed to create customer record for {messages[0].from_}"},
                        direction="system"
                    )
            
            # DUPLICATE FUNCTIONALITY FOR MARIADB CONTACTS TABLE
            # Check if contact exists in MariaDB contacts table
            try:
                from ..services.contact_service import ContactService
                contact_service = ContactService()
                
                # Look for an existing contact with this phone number
                query = """
                    SELECT id, name, user_id 
                    FROM contacts 
                    WHERE phone_number = %s
                """
                pool = await self.db.get_pool()
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(query, (messages[0].from_,))
                        contact_record = await cur.fetchone()
                
                if not contact_record:
                    logger.info(f"Contact Does Not Exist in Database - Creating new contact record for: {contact.profile.name} ({messages[0].from_})")
                    
                    # Insert the new WhatsApp contact (user_id is NULL - these are WhatsApp customers, not app users)
                    insert_query = """
                        INSERT INTO contacts (name, phone_number, user_id, created_at)
                        VALUES (%s, %s, NULL, NOW())
                    """
                    pool = await self.db.get_pool()
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(insert_query, (
                                contact.profile.name,
                                messages[0].from_,
                            ))
                    
                    logger.info(f"Successfully created contact record in database for {messages[0].from_}")
                else:
                    logger.debug(f"Contact already exists in database: {contact_record[1]} ({messages[0].from_})")
                    
                    # Update the contact name if it's different
                    if contact_record[1] != contact.profile.name:
                        update_query = """
                            UPDATE contacts
                            SET name = %s, updated_at = NOW()
                            WHERE id = %s
                        """
                        pool = await self.db.get_pool()
                        async with pool.acquire() as conn:
                            async with conn.cursor() as cur:
                                await cur.execute(update_query, (
                                    contact.profile.name,
                                    contact_record[0]
                                ))
                        logger.info(f"Updated contact name in database for {messages[0].from_}")
                        
            except Exception as e:
                log_whatsapp_message(
                    phone_number=messages[0].from_,
                    message_type="error",
                    message_data={"error": f"Error checking/updating contact in database: {str(e)}"},
                    direction="system"
                )
                # Continue processing even if the database operation fails
                # This ensures the Google Sheets functionality remains intact
            
            # Check if customer is in "Live Chat" mode - if so, skip AI processing
            # But don't skip if it's the admin's number
            admin_phone = os.getenv('ADMIN_WHATSAPP_NUMBER')
            is_admin = admin_phone and messages[0].from_ == admin_phone
            
            if customer and customer.get('chat_status') == "Live Chat" and not is_admin:
                logger.info(f"Customer {messages[0].from_} is in Live Chat mode. Skipping AI processing.")
                log_whatsapp_message(
                    phone_number=messages[0].from_,
                    message_type="system",
                    message_data={"message": "Live Chat mode active - AI processing skipped"},
                    direction="system"
                )
                return {"status": "success", "message": "Live Chat mode active - AI processing skipped"}
            elif customer and customer.get('chat_status') == "Live Chat" and is_admin:
                logger.info(f"Admin {messages[0].from_} is in Live Chat mode but will still get AI responses.")
                log_whatsapp_message(
                    phone_number=messages[0].from_,
                    message_type="system",
                    message_data={"message": "Admin override - AI processing continues despite Live Chat mode"},
                    direction="system"
                )
            
            # Process all messages
            content_items: List[Dict] = []
            thread_id = customer.get('thread_id') if customer else None
            
            # Add customer information as context at the beginning
            customer_context = f"Customer: {contact.profile.name}, Phone: {messages[0].from_}"
            content_items.append({
                "type": "text",
                "text": customer_context
            })
            
            for message in messages:
                if message.type == "text":
                    content_items.append({
                        "type": "text",
                        "text": message.text.body
                    })
                elif message.type == "image":
                    try:
                        # Download and optimize image
                        image_data = await self._download_media(message.image.id)
                        
                        # Upload to OpenAI and wait for processing
                        file_response = await self.upload_file(
                            image_data,
                            f"whatsapp_image_{message.image.id}.jpg"
                        )
                        
                        if not file_response or 'id' not in file_response:
                            raise ValueError("Failed to get valid file response from OpenAI")
                        logger.info(f"File uploaded successfully: {file_response['id']}")                            
                        
                        # Create image content dictionary
                        content_items.append({
                            "type": "image_file",
                            "image_file": {
                                "file_id": file_response["id"],
                                "detail": "high"
                            }
                        })
                        
                        # Add analysis instruction as text content
                        analysis_instruction = f"Mohon analisa gambar invoice ini dan ekstrak nomor invoice dan total pembayarannya."
                        content_items.append({
                            "type": "text",
                            "text": analysis_instruction
                        })
                        
                        if message.image.caption:
                            content_items.append({
                                "type": "text",
                                "text": "Caption: " + message.image.caption
                            })
                            
                    except Exception as e:
                        log_whatsapp_message(
                            phone_number=messages[0].from_,
                            message_type="error",
                            message_data={"error": f"Error processing image: {str(e)}"},
                            direction="system"
                        )
                        await self.send_message(
                            to=messages[0].from_,
                            message="Maaf, terjadi kesalahan saat memproses gambar. Mohon coba lagi."
                        )
                        return {"status": "error", "message": str(e)}

            # Get AI response with all message contents and metadata
            chat_response = await self.assistant_service.chat(ChatRequest(
                assistant_id=os.getenv("WHATSAPP_ASSISTANT_ID"),
                thread_id=thread_id,
                messages=[ChatMessage(
                    role="user",
                    content=content_items  # Send content_items directly
                )]
            ))
            
            # Update thread_id if needed
            # TODO: Might need to update thread if its outdated
            if customer and thread_id != chat_response.thread_id:
                logger.info(f"Updating thread_id for customer {customer['phone']} from {thread_id} to {chat_response.thread_id}")
                await update_thread_id(customer, chat_response.thread_id)
                
                # DUPLICATE FUNCTIONALITY FOR MARIADB CONTACTS
                try:
                    from ..services.contact_service import ContactService
                    contact_service = ContactService()
                    
                    # Also update the thread_id in the contacts table
                    await contact_service.update_thread_id(customer['phone'], chat_response.thread_id)
                except Exception as e:
                    log_whatsapp_message(
                        phone_number=customer['phone'],
                        message_type="error",
                        message_data={"error": f"Error updating thread_id in contacts table: {str(e)}"},
                        direction="system"
                    )
                    # Continue processing even if the database operation fails
            
            # Send response
            if chat_response.messages:
                assistant_message = next(
                    (msg for msg in chat_response.messages if msg.role == "assistant"),
                    None
                )

                if assistant_message and assistant_message.content:
                    # Handle the content directly as a string
                    response_text = assistant_message.content
                    
                    if response_text:
                        logger.info(f"Sending response to {messages[0].from_}: {response_text}")
                        
                        # Log outgoing message before sending
                        log_whatsapp_message(
                            phone_number=messages[0].from_,
                            message_type="text",
                            message_data={"text": response_text},
                            direction="outgoing"
                        )
                        
                        await self.send_message(
                            to=messages[0].from_,
                            message=response_text
                        )
                    else:
                        log_whatsapp_message(
                            phone_number=messages[0].from_,
                            message_type="error",
                            message_data={
                                "error": "No text content found in assistant response",
                                "debug": {
                                    "status": chat_response.status,
                                    "has_assistant_message": assistant_message is not None,
                                    "content_type": type(assistant_message.content).__name__ if assistant_message else None,
                                    "content_value": str(assistant_message.content) if assistant_message else None
                                }
                            },
                            direction="system"
                        )
                else:
                    log_whatsapp_message(
                        phone_number=messages[0].from_,
                        message_type="error",
                        message_data={
                            "error": "No assistant message or content found",
                            "debug": {
                                "status": chat_response.status,
                                "messages_count": len(chat_response.messages) if chat_response.messages else 0,
                                "has_assistant_message": assistant_message is not None,
                                "message_roles": [msg.role for msg in chat_response.messages] if chat_response.messages else [],
                                "run_error": chat_response.error
                            }
                        },
                        direction="system"
                    )
            else:
                log_whatsapp_message(
                    phone_number=messages[0].from_,
                    message_type="error",
                    message_data={
                        "error": "No messages in chat response",
                        "debug": {
                            "status": chat_response.status,
                            "thread_id": chat_response.thread_id
                        }
                    },
                    direction="system"
                )
            
            return {"status": "success"}
            
        except Exception as e:
            # Log the error with the phone number if available
            if 'messages' in locals() and messages and hasattr(messages[0], 'from_'):
                log_whatsapp_message(
                    phone_number=messages[0].from_,
                    message_type="error",
                    message_data={"error": f"Error processing webhook: {str(e)}"},
                    direction="system"
                )
            
            return {"status": "error", "message": str(e)}

    async def _download_media(self, media_id: str) -> bytes:
        """Download media from WhatsApp"""
        # First get media URL
        url = f"{self.base_url}/{media_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            # Get media URL
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Failed to get media URL: {response.text}")
            
            media_url = response.json().get("url")
            
            # Download media
            media_response = await client.get(media_url, headers=headers)
            if media_response.status_code != 200:
                raise ValueError("Failed to download media")
                
            return media_response.content
            
    async def send_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send a text message to a WhatsApp number"""
        # Format phone number
        formatted_to = to.replace("+", "").strip()
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": formatted_to,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": message
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                response_data = response.json()
                
                # Log the API response
                log_whatsapp_message(
                    phone_number=to,
                    message_type="api_response",
                    message_data=response_data,
                    direction="system"
                )
                
                if response.status_code != 200:
                    log_whatsapp_message(
                        phone_number=to,
                        message_type="error",
                        message_data={"error": f"Error sending message: {response.text}"},
                        direction="system"
                    )
                    return {"status": "error", "message": response.text}
                
                return {"status": "success", "data": response_data}
                
        except Exception as e:
            # Log the error
            log_whatsapp_message(
                phone_number=to,
                message_type="error",
                message_data={"error": f"Error sending message: {str(e)}"},
                direction="system"
            )
            
            return {"status": "error", "message": str(e)}