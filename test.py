from database import execute_query, fetch_query, init_db
from credentials import BOT_TOKEN, CHANNEL_ID, REPORT_ID
import asyncio
import re
import logging
import json

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

async def get_msg_ids():
    query = """
        SELECT msg_id
        FROM messages;
    """
    msg_ids = await fetch_query(query)
    
    for msg_id in msg_ids:
        report_text[msg_id['msg_id']] = 0

async def get_users_for_send_messages():
    query = """
        SELECT u.user_id, u.name, m.msg_id, m.links
        FROM users u
        JOIN messages m ON u.msg_id = m.msg_id
        WHERE now() >= (u.updated_at + m.period);
    """
    await get_msg_ids()
    users = await fetch_query(query)
    await iterate_users(users)

async def update_user(user_id, msg_id):
    print(f"User id: {type(user_id)}, msg_id: {type(msg_id)}")
    query = f"""
        UPDATE users
        SET msg_id = $1, updated_at = now()
        WHERE user_id = $2::VARCHAR;
    """
    res = await execute_query(query, (msg_id+1, user_id))
    print(res)

async def extract_message_id(url):
    match = re.search(r'https://t\.me/c/\d+/(\d+)', url)
    return match.group(1) if match else None

async def get_message_id(link):
    message_id = await extract_message_id(link)
    return message_id

async def get_message_text_from_local(message_id):
    with open('extras/messages.json', 'r') as file:
        data = json.load(file)[message_id]
    return data

async def send_message(name, user_id, msg_id, links):
    global success
    success = True

    for link in list(links):
        if link.startswith("$msg"):
            message_id = link[1:]
            message_text = await get_message_text_from_local(message_id)

            try:
                await bot.send_message(user_id, message_text.replace("$name", name), disable_web_page_preview=True)
            except Exception as e:
                success = False
                logging.error(f"Error: {e}")

        else:
            message_id = await get_message_id(link)
            try:
                await bot.copy_message(user_id, CHANNEL_ID, message_id)
            except Exception as e:
                success = False
                logging.error(f"Error copy book: {e}")
    if success:
        print(f"Message sent to {name}")
        report_text[msg_id] += 1
        print(report_text)
        try:
            await update_user(user_id, msg_id)
        except Exception as e:
            logging.error(f"Error update user: {e}")


async def send_report():
    report = "Below is the report of the users who have been sent the messages:\n"
    for msg_id, count in report_text.items():
        report += f"Message {msg_id}: {count} users\n"
    await bot.send_message(REPORT_ID, report)
    report_text.clear()

async def iterate_users(users):
    for user in users:
        user_id = user["user_id"]
        name = user["name"]
        msg_id = user["msg_id"]
        links = json.loads(user["links"])
        try:
            await send_message(name, user_id, msg_id, links)
        except Exception as e:
            logging.error(f"Error iteration: {e}")
            continue
        await asyncio.sleep(0.05)
    await send_report()

@dp.message()
async def check_func(message: types.Message):
    if message.text == "/check":
        await get_users_for_send_messages()

async def checking():
    await init_db()
    await dp.start_polling(bot)

asyncio.run(checking())