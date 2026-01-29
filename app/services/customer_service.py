from ..database.mysql import MariaDBClient
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class GetCustomerResponse(BaseModel):
    id: str
    phone_number: str
    name: str

class CustomerService:
    def __init__(self):
        self.db = MariaDBClient()

    async def get_customer(self, phone_number: str, name: str, organization_id: str) -> GetCustomerResponse:
        """Get or create customer by phone number"""
        try:
            # Check if contact exists for this organization
            contact_query = """
                SELECT id, name, phone_number 
                FROM contacts 
                WHERE name = %s AND phone_number = %s AND organization_id = %s
            """
            contact = await self.db.fetch_one(contact_query, (name, phone_number, organization_id))
            
            if contact:
                return GetCustomerResponse(
                    id=str(contact[0]),
                    name=contact[1],
                    phone_number=contact[2]
                )
                
            # 3. Create new contact if not exists
            insert_query = """
                INSERT INTO contacts (name, phone_number, organization_id)
                VALUES (%s, %s, %s)
            """
            await self.db.execute(insert_query, (name, phone_number, organization_id))
            
            # 4. Fetch created contact
            contact = await self.db.fetch_one(contact_query, (name, phone_number, organization_id))
            
            if contact:
                return GetCustomerResponse(
                    id=str(contact[0]),
                    name=contact[1],
                    phone_number=contact[2]
                )
                
            if not contact:
                raise ValueError("Contact not found")

        except Exception as e:
            logger.error(f"Error getting customer: {str(e)}", exc_info=True)
            raise

customer_service = CustomerService()

# Expose functions at module level for backward compatibility
get_customer = customer_service.get_customer
