import asyncio
import json
import logging
import re

from database import execute_query, fetch_query
from credentials import CHANNEL_ID, REPORT_ID

# Precompile regex for efficiency.
MESSAGE_ID_REGEX = re.compile(r'https://t\.me/c/\d+/(\d+)')

# Load the local messages cache once.
try:
    with open('extras/messages.json', 'r') as file:
        MESSAGES_CACHE = json.load(file)
except Exception as e:
    logging.error(f"Error loading messages.json: {e}")
    MESSAGES_CACHE = {}

async def extract_message_id(url: str) -> str:
    """Extract the message ID from a Telegram link."""
    match = MESSAGE_ID_REGEX.search(url)
    return match.group(1) if match else None

async def get_message_text_from_local(message_id: str) -> str:
    """Retrieve a message text from the local cache."""
    return MESSAGES_CACHE.get(message_id, "")

async def update_user(user_id: str, current_msg_id: int) -> None:
    """Update the user’s record by incrementing the message id."""
    new_msg_id = current_msg_id + 1
    query = """
        UPDATE users
        SET msg_id = $1, updated_at = now()
        WHERE user_id = $2;
    """
    await execute_query(query, (new_msg_id, user_id))
    logging.info(f"Updated user {user_id} to msg_id {new_msg_id}")

async def send_message(bot, name: str, user_id: str, msg_id: int, links: list, report: dict) -> None:
    """
    Send messages to a user.
    :param bot: The aiogram Bot instance.
    """
    success = True
    for link in links:
        try:
            if link.startswith("$msg"):
                # Use local message.
                message_key = link[1:]
                message_text = await get_message_text_from_local(message_key)
                if not message_text:
                    logging.error(f"No local message found for key '{message_key}'")
                    success = False
                    continue
                personalized_text = message_text.replace("$name", name)
                await bot.send_message(user_id, personalized_text, disable_web_page_preview=True)
            else:
                # Copy message from the channel.
                message_id_extracted = await extract_message_id(link)
                if not message_id_extracted:
                    logging.error(f"Failed to extract message id from link: {link}")
                    success = False
                    continue
                await bot.copy_message(user_id, CHANNEL_ID, message_id_extracted)
        except Exception as e:
            success = False
            logging.error(f"Error sending message for user {user_id} with link {link}: {e}")

    if success:
        logging.info(f"Message sent successfully to {name} (user_id: {user_id})")
        report[msg_id] = report.get(msg_id, 0) + 1
        try:
            await update_user(user_id, msg_id)
        except Exception as e:
            logging.error(f"Error updating user {user_id}: {e}")

async def send_report(bot, report: dict) -> None:
    """Compile and send a report to a designated channel."""
    lines = ["Below is the report of the users who have been sent the messages:"]
    for msg_id, count in report.items():
        lines.append(f"Message {msg_id}: {count} users")
    report_text = "\n".join(lines)
    try:
        await bot.send_message(REPORT_ID, report_text)
    except Exception as e:
        logging.error(f"Error sending report: {e}")

async def process_users(bot, users: list, report: dict) -> None:
    """Process users concurrently with a semaphore to limit concurrency."""
    semaphore = asyncio.Semaphore(10)  # Limit concurrency to 10 tasks.

    async def process_single_user(user: dict) -> None:
        async with semaphore:
            try:
                user_id = user["user_id"]
                name = user["name"]
                msg_id = user["msg_id"]
                links = user["links"]
                if isinstance(links, str):
                    links = json.loads(links)
                await send_message(bot, name, user_id, msg_id, links, report)
                await asyncio.sleep(0.05)
            except Exception as e:
                logging.error(f"Error processing user {user.get('user_id')}: {e}")

    tasks = [process_single_user(user) for user in users]
    await asyncio.gather(*tasks)

async def get_users_for_send_messages(bot) -> None:
    """
    Fetch users due for receiving messages and process them.
    :param bot: The aiogram Bot instance.
    """
    # Initialize the report with message IDs.
    query = "SELECT msg_id FROM messages;"
    rows = await fetch_query(query)
    report = {row['msg_id']: 0 for row in rows}

    query = """
        SELECT u.user_id, u.name, m.msg_id, m.links
        FROM users u
        JOIN messages m ON u.msg_id = m.msg_id
        WHERE now() >= (u.updated_at + m.period);
    """
    try:
        users = await fetch_query(query)
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        return

    if users:
        await process_users(bot, users, report)
        await send_report(bot, report)
    else:
        logging.info("No users to process at this time.")