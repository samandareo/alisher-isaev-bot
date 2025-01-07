import asyncpg
from contextlib import asynccontextmanager
import logging

# ------------------- DATABASE CONFIGURATION ------------------- #
# DATABASE_CONFIG = {
#     'host': "135.181.44.193",
#     'database': "isaevdb",
#     'user': "isaevpr",
#     'password': "isaevpr1234",
#     'port': "5432"
# }

# Test database
DATABASE_CONFIG ={
    'host': "localhost",
    'database': "testdb",
    'user': "postgres",
    'password': "sm1234",
    'port': "5432"
}
pool = None

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    global pool
    if pool is None:
        try:
            pool = await asyncpg.create_pool(
                user=DATABASE_CONFIG['user'],
                password=DATABASE_CONFIG['password'],
                database=DATABASE_CONFIG['database'],
                host=DATABASE_CONFIG['host'],
                port=DATABASE_CONFIG['port'],
                min_size=1,
                max_size=10
            )
            logger.info("Database pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

@asynccontextmanager
async def get_db_connection():
    if pool is None:
        raise RuntimeError("Database pool is not initialized. Call init_db() first.")
    try:
        async with pool.acquire() as conn:
            yield conn
    except Exception as e:
        logger.error(f"Error acquiring database connection: {e}")
        raise

# ------------------- DATABASE OPERATIONS ------------------- #
async def fetch_query(query, params=None):
    try:
        async with get_db_connection() as conn:
            result = await conn.fetch(query, *(params or []))
        return result
    except Exception as e:
        logger.error(f"Error executing fetch query: {e}")
        raise

async def execute_query(query, params=None):
    try:
        async with get_db_connection() as conn:
            await conn.execute(query, *(params or []))
        logger.info("Query executed successfully.")
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise

"""
Return value as below format:
(Record id=1 name='John Doe' age=25)

You can take them with their keys like:
result[0]['id']
result[0]['name']

OR

result[1]['id']
result[1]['name']

result[0] is the first row of the result.
"""
