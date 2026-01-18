import os
import aiomysql
import logging
from typing import Optional, List, Dict, Any, Tuple, Union

logger = logging.getLogger(__name__)

class MariaDBClient:
    def __init__(self):
        self.pool = None
        
    async def get_pool(self):
        """Get or create connection pool"""
        if self.pool is None:
            try:
                self.pool = await aiomysql.create_pool(
                    host=os.getenv('MARIADB_HOST', 'localhost'),
                    port=int(os.getenv('MARIADB_PORT', 3306)),
                    user=os.getenv('MARIADB_USER', 'root'),
                    password=os.getenv('MARIADB_PASSWORD', ''),
                    db=os.getenv('MARIADB_DATABASE', 'solutionesia_ai_whatsapp'),
                    autocommit=True
                )
            except Exception as e:
                logger.error(f"Error creating MariaDB pool: {str(e)}")
                raise
        return self.pool

    async def execute(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """Execute a query and return the last row id"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    logger.debug(f"Executing query: {query}")
                    await cur.execute(query, params)
                    
                    if query.upper().startswith('INSERT'):
                        lastrowid = cur.lastrowid
                        rowcount = cur.rowcount
                        logger.debug(f"Insert successful - lastrowid: {lastrowid}, rowcount: {rowcount}")
                        return {
                            "id": lastrowid,
                            "affected_rows": rowcount
                        }
                    return None
                except Exception as e:
                    logger.error(f"Error executing query: {str(e)}", exc_info=True)
                    raise

    async def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Tuple]:
        """Fetch a single row"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(query, params)
                    return await cur.fetchone()
                except Exception as e:
                    logger.error(f"Error fetching row: {str(e)}")
                    raise

    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Tuple]:
        """Fetch all rows"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(query, params)
                    return await cur.fetchall()
                except Exception as e:
                    logger.error(f"Error fetching rows: {str(e)}")
                    raise

    async def close(self):
        """Close the connection pool"""
        if self.pool is not None:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None 