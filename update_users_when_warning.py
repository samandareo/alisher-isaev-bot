from database import execute_query, fetch_query, init_db
from credentials import BOT_TOKEN, CHANNEL_ID, REPORT_ID
import asyncio
import re
import logging
import json

from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(lineno)s => %(message)s")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

global report_text
report_text = {

}


async def get_users_for_send_messages():
    query = """
        SELECT u.user_id, u.name, (u.updated_at + m.period) AS time, m.msg_id, m.links
        FROM users u
        JOIN messages m ON u.msg_id = m.msg_id
        WHERE now() >= (u.updated_at + m.period);
    """
    users = await fetch_query(query)
    await iterate_users(users)

async def update_user(user_id, msg_id, time):
    print(f"User id: {type(user_id)}, msg_id: {type(msg_id)}")
    query = f"""
        UPDATE users
        SET msg_id = $1, updated_at = $2
        WHERE user_id = $3::VARCHAR;
    """
    res = await execute_query(query, (msg_id+1,time,user_id))
    print(res)


async def iterate_users(users):
    for user in users:
        user_id = user["user_id"]
        name = user["name"]
        msg_id = user["msg_id"]
        time = user["time"]
        try:
            print(time)
            # await update_user(user_id, msg_id, time)
        except Exception as e:
            logging.error(f"Error iteration: {e}")
            continue
        await asyncio.sleep(0.05)

async def checking():
    await init_db()
    await get_users_for_send_messages()


asyncio.run(checking())