import asyncio
import logging
import sys
import re
import json


from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters.command import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, FSInputFile, Poll, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramRetryAfter
from aiogram.utils.markdown import link
from database import execute_query, fetch_query, init_db
import functions as fns
from State.userState import UserState, AdminState, AdminStateOne, UserMessagesToAdmin, CreatePoll, PollResults, ChangeBooks, WelcomePoll
import Keyboards.keyboards as kb

from credentials import admins, CHANNEL_ID

# send messages for users
from messaging import get_users_for_send_messages, reload_messages_cache


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()



from credentials import BOT_TOKEN, CHANNEL_ID, APPEAL_CHANNEL_ID, TEST_BOT_TOKEN, REPORT_ID, BOT_USERNAME
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

@dp.poll()
async def handler_poll(poll: Poll):
    poll_id = poll.id
    question = poll.question
    options = poll.options

    data = {
        'question' : question
    }
    print(f"Poll ID: {poll_id}, Question: {question}")
    for option in options:
        data[option.text] = option.voter_count
        print(f"Option: {option.text}, Voter Count: {option.voter_count}")
    
    await fns.change_data(poll_id,data)

@dp.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    await fns.handle_start_message(message, state=state)


@dp.message(WelcomePoll.user_fullname)
async def take_fullname(message: Message, state: FSMContext) -> None:
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi!")
        await state.clear()
        return
    await state.update_data(user_fullname=message.text)
    await message.reply("Iltimos, telefon raqamingizni kiriting:", reply_markup=kb.request_phone_number)
    await state.set_state(WelcomePoll.user_phone)

@dp.message(WelcomePoll.user_phone)
async def take_phone(message: Message, state: FSMContext) -> None:
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi!")
        await state.clear()
        return
    await state.update_data(user_phone=message.contact.phone_number)
    temporary_msg =await message.reply("Qabul qilindi!", reply_markup=ReplyKeyboardRemove())
    await temporary_msg.delete()
    await message.answer("Qaysi soha vakilisiz?", reply_markup=kb.user_jobs)
    await state.set_state(WelcomePoll.user_job)

@dp.callback_query(WelcomePoll.user_job)
async def take_job(callback_data: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    adding_info_query = f"INSERT INTO user_poll (user_id, user_fullname, phone_number, job, date, referred_by) VALUES ($1, $2, $3, $4, NOW(), $5) ON CONFLICT (user_id) DO NOTHING"
    await execute_query(adding_info_query,(str(callback_data.from_user.id), data['user_fullname'], data['user_phone'], callback_data.data, str(data['referred_by'])))
    await callback_data.message.reply(f"Savollarimizga javob berganingiz uchun tashakkur {data.get('user_fullname')}!", reply_markup=kb.main_menu_button)
    await state.clear()
    return
    
@dp.message(UserState.message_text_id)
async def take_id(message: Message, state: FSMContext) -> None:
    with open('extras/messages.json', 'r') as file:
        data = json.load(file)

    stop_msg_text = str(message.text)
    if stop_msg_text == '!cancel':
        await state.clear()
        await message.reply("Jarayon bekor qilindi!")
        return
    elif message.text.startswith('start_msg'):
        await state.update_data(message_text_id=message.text)
        if message.text not in data:
            await message.reply("Bunday raqamli /start xabar topilmadi! Demak yangi xabar sifatida qo'shamiz.")
            await message.reply("Yangi xabar matnini kiriting:")
            await state.set_state(UserState.message_text)
        elif message.text in data:
            message_text = data[message.text]
            await message.reply(f"Xabarning hozirgi holati: {message_text}\n\nIltimos yangi xabar matnini kiriting:")
            await state.set_state(UserState.message_text)
    elif message.text.startswith('msg'):
        await state.update_data(message_text_id=message.text)
        if message.text not in data:
            await message.reply("Bunday raqamli xabar topilmadi! Demak yangi xabar sifatida qo'shamiz.")
            await message.reply("Yangi xabar matnini kiriting:")
            await state.set_state(UserState.message_text)
        elif message.text in data:
            message_text = data[message.text]
            await message.reply(f"Xabarning hozirgi holati: {message_text}\n\nIltimos yangi xabar matnini kiriting:")
            await state.set_state(UserState.message_text)
    else:
        await message.reply("Noto'g'ri raqam kiritildi! Iltimos qaytadan urinib ko'ring.")
        await state.set_state(UserState.message_text_id)

@dp.message(UserState.message_text)
async def take_text(message: Message, state: FSMContext) -> None:
    if message.text == '!cancel':
        await state.clear()
        await message.reply("Jarayon bekor qilindi!")
        return
    
    with open('extras/messages.json', 'r') as file:
        data = json.load(file)

    new_data = await state.get_data()
    message_text_id = new_data.get('message_text_id')
    message_text = message.text

    data[message_text_id] = message_text

    with open('extras/messages.json', 'w') as file:
        json.dump(data, file, indent=4)

    await message.answer(f"{message_text_id} - xabar o'zgartirildi.")
    await state.clear()

broadcast_task = None

async def rasilka(users, message):
    global broadcast_task
    cnt = 0
    for user in users:
        if broadcast_task is not None and broadcast_task.cancelled():
            print("Vazifa bekor qilindi!")
            await message.reply(f"Xabar {cnt} ta foydalanuvchiga jo'natildi!")
            break
        try:
            if message.text:
                await bot.send_message(user['user_id'],message.text.replace("$name", user['name']), disable_web_page_preview=True)
            elif message.caption:
                await bot.copy_message(user['user_id'],message.chat.id,message.message_id, caption=message.caption.replace("$name", user['name']), protect_content=True)
            elif not message.text and not message.caption:
                await bot.copy_message(user['user_id'],message.chat.id,message.message_id, protect_content=True)
            print(f"Message sent to {user['name']} ({user['user_id']})")
            cnt += 1
        except TelegramRetryAfter as e:
            print(f'Rate limit exceeded. Sleeping for {e.timeout} seconds.')
            await asyncio.sleep(e.timeout)
            if message.text:
                await bot.send_message(user['user_id'],message.text.replace("$name", user['name']), disable_web_page_preview=True)
            elif message.caption:
                await bot.copy_message(user['user_id'],message.chat.id,message.message_id, caption=message.caption.replace("$name", user['name']), protect_content=True)
            elif not message.text and not message.caption:
                await bot.copy_message(user['user_id'],message.chat.id,message.message_id, protect_content=True)
            print(f"Message sent to {user['name']} ({user['user_id']})")
            cnt += 1

        except Exception as e:
            if 'Forbidden' in str(e):
                await execute_query(f"DELETE FROM users WHERE users.user_id = '{user['user_id']}';")
            print(e)
            continue
        print(f"Message sent to {user['name']} ({user['user_id']})")
        await asyncio.sleep(0.05)
    await message.answer(f"Xabar {cnt} ta foydalanuvchiga jo'natildi!")

async def rasilka_copy(users, message):
    global broadcast_task
    cnt = 0
    for user in users:
        if broadcast_task is not None and broadcast_task.cancelled():
            print("Vazifa bekor qilindi!")
            await message.reply(f"Xabar {cnt} ta foydalanuvchiga jo'natildi!")
            break
        try:
            await bot.copy_message(user['user_id'],message.chat.id,message.message_id, protect_content=True)
            print(f"Message sent to {user['name']} ({user['user_id']})")
            cnt += 1
        except TelegramRetryAfter as e:
            print(f'Rate limit exceeded. Sleeping for {e.timeout} seconds.')
            await asyncio.sleep(e.timeout)
            await bot.copy_message(user['user_id'],message.chat.id,message.message_id, protect_content=True)
            print(f"Message sent to {user['name']} ({user['user_id']})")
            cnt += 1

        except Exception as e:
            if 'Forbidden' in str(e):
                await execute_query(f"DELETE FROM users WHERE users.user_id = '{user['user_id']}';")
            print(e)
            continue
        print(f"Message sent to {user['name']} ({user['user_id']})")
        await asyncio.sleep(0.05)
    await message.answer(f"Xabar {cnt} ta foydalanuvchiga jo'natildi!")

@dp.callback_query(AdminState.admin_action)
async def choose_action(callback_data: CallbackQuery, state: FSMContext) -> None:
    if callback_data.data == 'send_type_message':
        await callback_data.message.answer("Xabar matnini yuboring")
        await state.set_state(AdminState.send_type_message)
    elif callback_data.data == 'copy_type_message':
        await callback_data.message.answer("Xabar matnini yuboring")
        await state.set_state(AdminState.copy_type_message)

@dp.message(AdminState.send_type_message)
async def send_to_all(message: Message, state: FSMContext) -> None:
    global brodcast_task
    message_text = message.text
    if message_text == "!cancel":
        await message.reply("Jarayon bekor qilindi!")
        await state.clear()
        return
    
    users = await fetch_query("SELECT user_id, name FROM users;")
    # We need to run the function in a separate task to avoid blocking the event loop
    try:
        brodcast_task = asyncio.create_task(rasilka(users, message))
        await message.answer("Rasilka boshlandi!")
    except Exception as e:
        logger.info(f"Error sending message to users: {e}")

    await state.clear()

@dp.message(AdminState.copy_type_message)
async def copy_to_all(message: Message, state: FSMContext) -> None:
    global broadcast_task
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    users = await fetch_query("SELECT user_id, name FROM users;")
    try:
        broadcast_task = asyncio.create_task(rasilka_copy(users, message))
        await message.answer("Rasilka boshlandi!")
    except Exception as e:
        logger.info(f"Error sending message to users: {e}")
    await state.clear()

@dp.callback_query(AdminStateOne.admin_action)
async def choose_action_one(callback_data: CallbackQuery, state: FSMContext) -> None:
    if callback_data.data == 'send_type_message':
        await callback_data.message.answer("Foydalanuvchi ID raqamini kiriting!")
        await state.set_state(AdminStateOne.send_type_message)
    elif callback_data.data == 'copy_type_message':
        await callback_data.message.answer("Foydalanuvchi ID raqamini kiriting!")
        await state.set_state(AdminStateOne.copy_type_message)

@dp.message(AdminStateOne.send_type_message)
async def take_message_one(message: Message, state: FSMContext) -> None:
    msg_text = str(message.text)
    print(msg_text)
    if msg_text == '!cancel':
        await message.reply("Jarayon bekor qilindi!")
        await state.clear()
        return
    else:
        wait_message = await message.answer("Foydalanuvchi qidirilmoqda...")
        check = await fetch_query("SELECT * FROM users WHERE user_id = $1;", (msg_text,))

    if not check:
        await wait_message.edit_text("Foydalanuvchi topilmadi😕")
        await state.clear()
        return
    else:
        await state.update_data(user_id=message.text)
        found_msg_text = f"Foydalanuvchi topildi.\nUser ID: {check[0]['user_id']}\nName: {check[0]['name']}\nUsername: {check[0]['username']}\nPhone number: {check[0]['phone_number']}\n\nFoydalanuvchiga yuborishni xoxlagan xabarni kiriting."
        await wait_message.edit_text(found_msg_text)
        await state.set_state(AdminStateOne.message_text)

@dp.message(AdminStateOne.message_text)
async def send_to_one(message: Message, state: FSMContext) -> None:
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi!")
        await state.clear()
        return
    await state.update_data(message_text=message.text)
    new_data = await state.get_data()
    user_id = new_data.get('user_id')
    message_text = new_data.get('message_text')
    user = await fetch_query(f"SELECT name FROM users WHERE user_id = '{user_id}';")
    try:
        if message.text:
            await bot.send_message(chat_id=user_id,text=message_text.replace("$name", user[0]['name']), disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
        elif message.caption:
            await bot.copy_message(user_id,message.chat.id,message.message_id, caption=message.caption.replace("$name", user[0]['name']), parse_mode=ParseMode.MARKDOWN)
        elif not message.text and not message.caption:
            await bot.copy_message(user_id,message.chat.id,message.message_id, parse_mode=ParseMode.MARKDOWN)
        await message.answer("Xabar jo'natildi!")
    except Exception as e:
        if 'Forbidden' in str(e):
            await execute_query(f"DELETE FROM users WHERE users.user_id = '{user_id}';")
        print(e)
    await state.clear()

@dp.message(AdminStateOne.copy_type_message)
async def take_message_one(message: Message, state: FSMContext) -> None:
    msg_text = str(message.text)
    print(msg_text)
    if msg_text == '!cancel':
        await message.reply("Jarayon bekor qilindi!")
        await state.clear()
        return
    else:
        wait_message = await message.answer("Foydalanuvchi qidirilmoqda...")
        check = await fetch_query("SELECT * FROM users WHERE user_id = $1;", (msg_text,))

    if not check:
        await wait_message.edit_text("Foydalanuvchi topilmadi😕")
        await state.clear()
        return
    else:
        await state.update_data(user_id=message.text)
        found_msg_text = f"Foydalanuvchi topildi.\nUser ID: {check[0]['user_id']}\nName: {check[0]['name']}\nUsername: {check[0]['username']}\nPhone number: {check[0]['phone_number']}\n\nFoydalanuvchiga yuborishni xoxlagan xabarni kiriting."
        await wait_message.edit_text(found_msg_text)
        await state.set_state(AdminStateOne.copy_message_text)

@dp.message(AdminStateOne.copy_message_text)
async def send_to_one(message: Message, state: FSMContext) -> None:
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi!")
        await state.clear()
        return
    
    await state.update_data(message_text=message.text)
    new_data = await state.get_data()
    user_id = new_data.get('user_id')
    message_text = new_data.get('message_text')

    try:
        await bot.copy_message(user_id,message.chat.id,message.message_id, protect_content=True)
        await message.answer("Xabar jo'natildi!")
    except Exception as e:
        if 'Forbidden' in str(e):
            await execute_query(f"DELETE FROM users WHERE users.user_id = '{user_id}';")
        print(e)
    await state.clear()

@dp.message(UserMessagesToAdmin.message_text)
async def take_message(message: Message, state: FSMContext) -> None:
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    
    if message.text == 'Murojaat':
        await message.reply("Iltimos, murojaat xabarini yuboring.", reply_markup=ReplyKeyboardRemove())
        await state.set_state(UserMessagesToAdmin.message_text)
        return
    
    await state.update_data(message_text=message.text)
    await message.answer("Murojaatingizni tasdiqlaysizmi?", reply_markup=kb.proove_message)
    await state.set_state(UserMessagesToAdmin.message_proove)

@dp.callback_query(UserMessagesToAdmin.message_proove)
async def send_appeal(callback_data: CallbackQuery, state: FSMContext) -> None:
    if callback_data.data == "proove":
        data = await state.get_data()
        text = data.get('message_text')
        appeal = f"🔔🔔 Yangi Murojaat 🔔🔔\n\nFoydalanuvchi ID: {callback_data.from_user.id}\nFoydalanuvchi ismi: {callback_data.from_user.first_name}\nFoydalanuvchi username: @{callback_data.from_user.username}\n\nMurojaat xabari: {text}"


        try:
            await bot.send_message(chat_id=APPEAL_CHANNEL_ID,text=appeal, parse_mode=ParseMode.HTML)
            await callback_data.message.answer("Murojaatingiz qabul qilindi!",show_alert=True, reply_markup=kb.contact_with_admin)
            await callback_data.message.delete()
        except Exception as e:
            print(e)
    elif callback_data.data == "cancel":
        await callback_data.message.answer("Murojaatingiz bekor qilindi!", reply_markup=kb.contact_with_admin)
        await callback_data.message.delete()
    await state.clear()

@dp.message(CreatePoll.question)
async def take_question(message: Message, state: FSMContext) -> None:
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    
    await state.update_data(question=message.text)
    await message.reply("Qabul qilindi! So'rovnomada nechta javob/variant bo'lishi kerak?")
    await state.set_state(CreatePoll.count)

@dp.message(CreatePoll.count)
async def take_count(message: Message, state: FSMContext) -> None:
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    
    await state.update_data(count=int(message.text), options=[])
    await message.reply("Axa! Iltimos, 1 - variantni kiriting:")
    await state.set_state(CreatePoll.option)


@dp.message(CreatePoll.option)
async def take_options(message: Message, state: FSMContext) -> None:
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    
    user_data = await state.get_data()
    options = user_data.get('options', [])
    count = user_data.get('count')

    options.append(message.text)
    await state.update_data(options=options)

    if len(options) < count:
        await message.reply(f"Qabul qilindi! {len(options)+1}-variantni kiriting:")
        await state.set_state(CreatePoll.option)
        return
    else:
        question = user_data.get('question')
        options = user_data.get('options')
        text = ''
        for option in options:
            text += f"{option}\n"

        await message.reply(f"Savol : {question}\nVariantlar:\n{text}\n---------------------\nSo'rovnomani tasdiqlaysizmi?", reply_markup=kb.proove_poll)
        await state.set_state(CreatePoll.proove)

@dp.callback_query(CreatePoll.proove)
async def send_appeal(callback_data: CallbackQuery, state: FSMContext) -> None:
    if callback_data.data == 'proove':
        msg = await callback_data.message.answer("So'rovnoma yaratildi va yuborilmoqda...",show_alert=True, reply_markup=kb.contact_with_admin)
        await callback_data.message.delete()
        try:
            await bot.copy_message(chat_id=msg.chat.id, from_chat_id=-1002465539645, message_id=3, reply_to_message_id=msg.message_id)
        except Exception as e:
            print(e)
        data = await state.get_data()
        question = data.get('question')
        options = data.get('options')
        await fns.create_poll(question, options)
        await state.clear()
        print("Poll created")
        return
    
    elif callback_data.data == 'cancel':
        msg = await callback_data.message.reply("So'rovnoma bekor qilindi")
        await callback_data.message.delete()
        try:
            await bot.copy_message(chat_id=callback_data.message.chat.id, from_chat_id=-1002465539645, message_id=5, reply_to_message_id=msg.message_id)
        except Exception as e:
            print(e)
        await state.clear()
        print("Poll canceled")
        return

@dp.message(PollResults.poll_name)
async def take_poll_name(message: Message, state: FSMContext) -> None:
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    
    with open('polls/poll_ids.json', 'r') as file:
        data = json.load(file)
    
    polls = []

    for item in data:
        polls.append(item)
    
    poll_name = polls[int(message.text)-1]

    res = await fns.get_result(poll_name)
    text = f"Question: {res['question']}\n"
    for key, value in res.items():
        if key == 'question':
            continue
        text += f"{key}: {value}\n"
    
    await message.answer(text=text)
    await state.clear()
    return

# Change books -------------------------------------------------------------- #
@dp.callback_query(ChangeBooks.choose_action)
async def change_books(callback_data: CallbackQuery, state: FSMContext):
    if callback_data.data == 'add_book':
        await callback_data.message.answer("Kitob nomini kiriting:")
        await state.set_state(ChangeBooks.book_name)
    elif callback_data.data == 'edit_book':
        await callback_data.message.answer("O'zgartirish uchun kitob ID raqamini kiriting:")
        await state.set_state(ChangeBooks.book_id_edit)
    elif callback_data.data == 'remove_book':
        await callback_data.message.answer("O'chirish uchun kitob ID raqamini kiriting:")
        await state.set_state(ChangeBooks.book_id_delete)
    elif callback_data.data == 'cancel':
        await callback_data.message.delete()
        await state.clear()
        return

# Add book
@dp.message(ChangeBooks.book_name)
async def take_book_name_adding(message: Message, state: FSMContext):
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    await state.update_data(book_name=message.text)
    await message.answer("Kitob IDsini kiriting:")
    await state.set_state(ChangeBooks.book_id)

@dp.message(ChangeBooks.book_id)
async def take_book_id_adding(message: Message, state: FSMContext):
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    await state.update_data(book_id=message.text)
    await message.answer("Kitob linkini kiriting:")
    await state.set_state(ChangeBooks.book_link)

@dp.message(ChangeBooks.book_link)
async def take_book_link_adding(message: Message, state: FSMContext):
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    new_data = await state.get_data()
    book_name = new_data.get('book_name')
    book_id = int(new_data.get('book_id'))
    book_link = message.text
    status = await fns.add_book(book_name, book_id, book_link)
    if status == "success":
        await message.reply("Kitob qo'shildi!")
        await state.clear()
        books = await fns.show_books()
        await message.answer(books)
    else:
        await message.reply("Kitob qo'shilmadi. Iltimos qaytadan urinib ko'ring!")
        await state.clear()
        books = await fns.show_books()
        await message.answer(books)


# Edit book
@dp.message(ChangeBooks.book_id_edit)
async def take_book_id_editing(message: Message, state: FSMContext):
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    await state.update_data(book_id=message.text)
    await message.reply("Yangi kitob nomini kiriting:")
    await state.set_state(ChangeBooks.book_name_edit)

@dp.message(ChangeBooks.book_name_edit)
async def take_book_name_editing(message: Message, state: FSMContext):
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    await state.update_data(book_name=message.text)
    await message.reply("Yangi kitob linkini kiriting:")
    await state.set_state(ChangeBooks.book_link_edit)

@dp.message(ChangeBooks.book_link_edit)
async def take_book_link_editing(message: Message, state: FSMContext):
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    await state.update_data(book_link=message.text)
    await message.reply("Kitob ID raqamini o'zgartirishni hohlaysizmi?", reply_markup=kb.book_id_proove)
    await state.set_state(ChangeBooks.new_book_id_proove)

@dp.callback_query(ChangeBooks.new_book_id_proove)
async def change_book_id(callback_data: CallbackQuery, state: FSMContext):
    if callback_data.data == 'yes_change':
        await callback_data.message.delete()
        await callback_data.message.answer("Yangi kitob ID raqamini kiriting:")
        await state.set_state(ChangeBooks.book_new_id_edit)
    elif callback_data.data == 'no_change':
        new_data = await state.get_data()
        book_id = int(new_data.get('book_id'))
        book_name = new_data.get('book_name')
        book_link = new_data.get('book_link')
        status = await fns.edit_book(book_id, book_name, book_link)
        if status == "success":
            await callback_data.message.answer( "Kitob o'zgartirildi!")
            books = await fns.show_books()
            await callback_data.message.answer(books)
            await state.clear()
        else:
            await callback_data.message.answer("Kitob o'zgartirilmadi. Iltimos qaytadan urinib ko'ring!")
            await state.clear()

@dp.message(ChangeBooks.book_new_id_edit)
async def take_new_book_id_editing(message: Message, state: FSMContext):
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    
    try:
        new_data = await state.get_data()
        book_id = int(new_data.get('book_id'))
        book_name = new_data.get('book_name')
        book_link = new_data.get('book_link')
        new_book_id = int(message.text)
        status = await fns.edit_book(book_id, book_name, book_link, new_book_id)
    except Exception as e:
        logging.error(e)
        await message.reply("Kitob o'zgartirilmadi. Iltimos qaytadan urinib ko'ring!")
        await state.clear()
        return
    if status == "success":
        await message.reply("Kitob o'zgartirildi!")
        books = await fns.show_books()
        await message.answer(books)
        await state.clear()

#Delete book
@dp.message(ChangeBooks.book_id_delete)
async def take_book_id_deleting(message: Message, state: FSMContext):
    if message.text == '!cancel':
        await message.reply("Jarayon bekor qilindi")
        await state.clear()
        return
    status = await fns.delete_book(int(message.text))
    if status == "success":
        await message.reply("Kitob o'chirildi!")
        books = await fns.show_books()
        await message.answer(books)
        await state.clear()
    else:
        await message.reply(f"Kitob o'chirilmadi. {message.text} ID bilan kitob bo'lmasligi mumkin!\nIltimos qaytadan urinib ko'ring!")
        await state.clear()
        books = await fns.show_books()
        await message.answer(books)

    


@dp.message()
async def take_input(message: Message, state: FSMContext):
    if message.text == '/change_message':
        if message.from_user.id not in admins:
            await message.answer("Siz admin emassiz!")
            return
        await message.answer("Please enter the message number you want to change.(start with msg or start_msg)")
        await state.set_state(UserState.message_text_id)
        return
    elif message.text == '/send':
        if message.from_user.id not in admins:
            await message.answer("Siz admin emassiz!")
            return
        await message.answer("Qaysi turda yuborishni xoxlaysiz", reply_markup=kb.send_message_type)
        await state.set_state(AdminState.admin_action)
        return
    elif message.text == '/sendOne':
        if message.from_user.id not in admins:
            await message.answer("Siz admin emassiz!")
            return
        await message.answer("Foydalanuvchini ID raqamini kiriting.")
        await state.set_state(AdminStateOne.userOneId)
        return
    elif message.text == 'Murojaat':
        await message.reply("Iltimos, murojaat xabarini yuboring.", reply_markup=ReplyKeyboardRemove())
        await state.set_state(UserMessagesToAdmin.message_text)
        return
    elif message.text == '📊Statistika':
        res = await fns.get_statistic(str(message.from_user.id))
        await message.answer(res)
        return
    elif message.text == "🤝Do'stlarni taklif qilish":
        await message.reply(f"Quyidagi linkni orqali do'stlaringizni taklif qiling! Agarda 10 ta do'stingiz shu link orqali botimizga tashrif buyursa, siz maxsus qo'llanma va kitoblarga ega bo'lishingiz mumkin.\n\nLink: https://t.me/{BOT_USERNAME}?start=invite_{message.from_user.id}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Do'stlarga yuborish", url=f"https://t.me/share/url?&url=https://t.me/{BOT_USERNAME}?start=invite_{message.from_user.id}&text=Yuqoridagi link orqali botimizga tashrif buyuring va foydali ma'lumotlardan bahramand bo'ling!")]]))
        return
    elif message.text == '/stat':
        if message.from_user.id not in admins:
            await message.answer("Siz admin emassiz!")
            return
        users = await fetch_query("SELECT COUNT(*) FROM users;")
        await message.answer(f"Botda {users[0]['count']} ta foydalanuvchi mavjud.")
        return
    elif message.text == '/users':
        if message.from_user.id not in admins:
            await message.answer("Siz admin emassiz!")
            return
        path = await fns.get_users_data_as_excel()
        if path:
            file = FSInputFile(path,filename=path[7:])
            await bot.send_document(chat_id=message.chat.id, document=file,caption="Foydalanuvchilar ro'yxati")
    elif message.text == '/registered_users':
        if message.from_user.id not in admins:
            await message.answer("Siz admin emassiz!")
            return
        path = await fns.get_registered_users()
        if path:
            file = FSInputFile(path,filename=path[7:])
            await bot.send_document(chat_id=message.chat.id, document=file,caption="Ro'yxatdan o'tgan foydalanuvchilar ro'yxati")

    elif message.text == '/refresh':
        if message.from_user.id not in admins:
            await message.answer("Siz admin emassiz!")
            return
        try:
            await reload_messages_cache()
            await message.answer("Messages cache reloaded successfully.")
        except Exception as e:
            await message.answer(f"Error reloading messages.json: {e}")
    elif message.text == '/polls':
        if message.text == '!cancel':
            await message.reply("Jarayon bekor qilindi")
            await state.clear()
            return
        names = []
        text = ''

        with open('polls/poll_ids.json', 'r') as file:
            data = json.load(file)
            
        count = 1   
        for item in data:
            names.append(item)
            text += f"{count}. {item}\n"
            count += 1

        req = "Tanlagan so'rovnomangizni raqamini kriting:"
        full_text = f"{text}\n{req}"
        await message.answer(text=full_text)
        await state.set_state(PollResults.poll_name)
        return
    elif message.text == '/create_poll':
        await message.reply("So'rovnoma savolini kiriting!")
        await state.set_state(CreatePoll.question)
        return
    elif message.text == '/stop_rasilka':
        global brodcast_task
        if brodcast_task is not None and not brodcast_task.cancelled():
            brodcast_task.cancel()
            await message.answer("Rasilkani to'xtatish uchun buyruq qabul qilindi.")
        else:
            await message.answer("Rasilkani to'xtatish uchun hech qanday buyruq qabul qilinmadi.")
        return
    elif message.text == '/books':
        if message.from_user.id not in admins:
            await message.answer("Siz admin emassiz!")
            return
        if message.text == '!cancel':
            await message.reply("Jarayon bekor qilindi")
            await state.clear()
            return
        
        books = await fns.show_books()
        await message.reply(books, reply_markup=kb.change_books)
        await state.set_state(ChangeBooks.choose_action)
        return
        

@scheduler.scheduled_job('interval', minutes=10)
async def scheduler_task():
    await get_users_for_send_messages(bot=bot)



async def main() -> None:
    await init_db()
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
