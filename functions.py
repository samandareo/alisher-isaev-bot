import asyncio
import json
import logging
import re
from datetime import datetime, timedelta


from database import execute_query, fetch_query, init_db
from bot import bot
logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(lineno)s => %(message)s")

from credentials import REPORT_ID, CHANNEL_ID
import Keyboards.keyboards as kb
from State.userState import WelcomePoll

from messaging import extract_message_id
import pandas as pd


async def get_users(time, msg_id):
    try:
        if not isinstance(msg_id, tuple):
            msg_id = tuple(msg_id)
        query = """
        SELECT bu.user_id, bu.username, bu.name, bu.cur_msg_id, bu.res_id 
        FROM users as bu 
        LEFT JOIN end_users as eu ON bu.phone_number = eu.phone_number 
        WHERE eu.phone_number IS NULL 
            AND bu.updated_at <= $1 
            AND bu.cur_msg_id = ANY($2::int[]) 
            AND bu.is_check = true;
        """
        params = (time, list(msg_id))
        return await fetch_query(query=query, params=params)
    except Exception as e:
        print(e)
        return None

async def get_users_for_first(time):
    await init_db()
    try:
        query = """
        SELECT bu.user_id,bu.username, bu.name, bu.cur_msg_id, bu.res_id 
        FROM users as bu 
        LEFT JOIN end_users as eu ON bu.phone_number = eu.phone_number
        WHERE eu.phone_number IS NULL 
          AND bu.created_at <= $1
          AND bu.cur_msg_id = 1 
          AND bu.is_check = true;
        """
        params = (time,)
        return await fetch_query(query=query, params=params)
    except Exception as e:
        print(e)
        return None

async def send_first_message():
    with open('extras/messages.json', 'r') as file:
        data = json.load(file)['msg1']

    time = datetime.now() - timedelta(hours=24)
    users = await get_users_for_first(time=time)
    print(users)
    if not users:
        print('No users')
        return

    await bot.send_message(chat_id=REPORT_ID,text=f"Birinchi xabar yuborilishi boshlandi!")
    cnt = 0
    for user in users:
        msg_id = user['cur_msg_id'] + 1
        txt = str(data)
        txt = txt.replace('$name', user['name'])
        try:

            # # This userbot ------ #
            # if user['username']:
            #     try:
            #         await send_to_users(username=user['username'], message_text=txt, respon_id=user['res_id'])
            #     except Exception as e:
            #         print(e)
            # # ------------------- #

            await bot.send_message(chat_id=user['user_id'], text=data.replace('$name', user['name']), disable_web_page_preview=True)
            await asyncio.sleep(1)
            await execute_query("UPDATE users SET updated_at = $1, cur_msg_id = $2 WHERE user_id = $3;", (datetime.now(), msg_id, user['user_id']))
        except Exception as e:
            if 'Forbidden' in str(e):
                await execute_query("DELETE FROM users WHERE user_id = $1;", (user['user_id'],))
            print(e)
            continue
        print(f"Message sent to {user['name']} ({user['user_id']})")
        await asyncio.sleep(0.7)
        cnt += 1
    await bot.send_message(chat_id=REPORT_ID,text=f"Birinchi xabar {cnt} ta foydalanuvchiga xabar yuborildi✅")

async def send_24_messages():
    with open('extras/messages.json', 'r') as file:
        data = json.load(file)

    time = datetime.now() - timedelta(hours=24)
    users = await get_users(time, [2, 4, 5, 6, 8])

    if not users:
        print('No users')
        return
    await bot.send_message(chat_id=REPORT_ID,text=f"24 soatlik xabarlar yuborilishi boshlandi!")

    cnt = {
        2: 0,
        4: 0,
        5: 0,
        6: 0,
        8: 0
    }

    for user in users:
        msg_id = user['cur_msg_id'] + 1
        if user['cur_msg_id'] != 4:
            try:
                # # This userbot ------ #
                # if user['username']:
                #     txt = str(data[f"msg{user['cur_msg_id']}"])
                #     try:
                #         await send_to_users(username=user['username'], message_text=txt.replace('$name', user['name']), respon_id=user['res_id'])
                #     except Exception as e:
                #         print(e)
                # # ------------------- #

                await bot.send_message(chat_id=user['user_id'], text=data[f"msg{user['cur_msg_id']}"].replace('$name', user['name']), disable_web_page_preview=True)
                # await execute_query("UPDATE users SET updated_at = $1, cur_msg_id = $2 WHERE user_id = $3;", (datetime.now(), msg_id, user['user_id']))
                await asyncio.sleep(1)
                await execute_query("UPDATE users SET updated_at = $1, cur_msg_id = $2 WHERE user_id = $3;", (datetime.now(), msg_id, user['user_id']))
            except Exception as e:
                if 'Forbidden' in str(e):
                    await execute_query("DELETE FROM users WHERE user_id = $1;", (user['user_id'],))
                print(e)
                continue
            print(f"Message sent to {user['name']} ({user['user_id']})")

        elif user['cur_msg_id'] == 4:
            txt1 = str(data[f"msg{user['cur_msg_id']}1"])
            txt2 = str(data[f"msg{user['cur_msg_id']}2"])
            try:

                # # This userbot ------ #
                # if user['username']:
                #     try:
                #         await send_to_users(username=user['username'], message_text=txt1.replace('$name', user['name']), respon_id=user['res_id'])
                #         await copy_to_users(username=user['username'], channel_id=-1002151076535, respon_id=user['res_id'], message_id=18)
                #         await send_to_users(username=user['username'], message_text=txt2.replace('$name', user['name']), respon_id=user['res_id'])
                #     except Exception as e:
                #         print(e)
                # # ------------------- #

                await bot.send_message(chat_id=user['user_id'], text=data[f"msg{user['cur_msg_id']}1"].replace('$name', user['name']), disable_web_page_preview=True)
                await asyncio.sleep(0.1)
                await bot.copy_message(chat_id=user['user_id'], from_chat_id=-1002151076535, message_id=18)
                await asyncio.sleep(0.1)
                await bot.send_message(chat_id=user['user_id'], text=data[f"msg{user['cur_msg_id']}2"].replace('$name', user['name']), disable_web_page_preview=True)
                await asyncio.sleep(0.1)
                await execute_query("UPDATE users SET updated_at = $1, cur_msg_id = $2 WHERE user_id = $3;", (datetime.now(), msg_id, user['user_id']))

            except Exception as e:
                if 'Forbidden' in str(e):
                    await execute_query("DELETE FROM users WHERE user_id = $1;", (user['user_id'],))
                print(e)
                continue
            print(f"Message sent to {user['name']} ({user['user_id']})")
        await asyncio.sleep(0.7)
        cnt[user['cur_msg_id']] += 1

    done_msg = f"Foydalanuvchilarga yuborilgan xabarlar soni:\nIkkinchi xabar soni: {cnt.get(2)}\nTo'rtinchi xabar soni: {cnt.get(4)}\nBeshinchi xabar soni: {cnt.get(5)}\nOltinchi xabar soni: {cnt.get(6)}\nSakkizinchi xabar soni: {cnt.get(8)}"
    await bot.send_message(chat_id=REPORT_ID,text=done_msg)
    cnt = {
        2: 0,
        4: 0,
        5: 0,
        6: 0,
        8: 0
    }

async def send_48_messages():
    with open('extras/messages.json', 'r') as file:
        data = json.load(file)

    time = datetime.now() - timedelta(hours=48)
    users = await get_users(time, [3, 7])

    if not users:
        print('No users')
        return
    
    cnt = {
        3: 0,
        7: 0
    }
    for user in users:
        msg_id = user['cur_msg_id'] + 1
        try:

            # # This userbot ------ #
            # if user['username']:
            #     txt = str(data[f"msg{user['cur_msg_id']}"])
            #     try:
            #         await send_to_users(username=user['username'], message_text=txt.replace('$name', user['name']), respon_id=user['res_id'])
            #     except Exception as e:
            #         print(e)
            # # ------------------- #

            await bot.send_message(chat_id=user['user_id'], text=data[f"msg{user['cur_msg_id']}"].replace('$name', user['name']), disable_web_page_preview=True)
            await asyncio.sleep(0.1)
            await execute_query("UPDATE users SET updated_at = $1, cur_msg_id = $2 WHERE user_id = $3;", (datetime.now(), msg_id, user['user_id']))
        except Exception as e:
            if 'Forbidden' in str(e):
                await execute_query("DELETE FROM users WHERE user_id = $1;", (user['user_id'],))
            print(e)
            continue
        await asyncio.sleep(0.7)
        cnt[user['cur_msg_id']] += 1

    done_msg = f"Foydalanuvchilarga yuborilgan xabarlar soni:\nUchinchi xabar soni: {cnt.get(3)}\nYettinchi xabar soni: {cnt.get(7)}"
    await bot.send_message(chat_id=REPORT_ID,text=done_msg)
    cnt = {
        3: 0,
        7: 0
    }




async def send_message_to_users():
    try:
        await send_first_message()
        await asyncio.sleep(1)
        await send_24_messages()
        await asyncio.sleep(1)
        await send_48_messages()
    except Exception as e:
        print(e)

# To run the functions
# asyncio.run(send_message_to_users())

async def get_users_data_as_excel():
    try:
        query = """
        SELECT user_id, username, name, phone_number, DATE(created_at) 
        FROM users
        """
        data = await fetch_query(query=query)
        if not data:
            return None
        df = pd.DataFrame(data)

        df.columns = ['user_id', 'username', 'name', 'phone_number', 'created_at']
        print(df)
        new_data = {
            'user_id': [],
            'username': [],
            'name': [],
            'phone_number': [],
            'created_at': []
        }

        for i in range(len(df)):
            new_data['user_id'].append(df['user_id'][i])
            new_data['username'].append(df['username'][i])
            new_data['name'].append(df['name'][i])
            if str(df['phone_number'][i]) == 'None':
                new_data['phone_number'].append("Phone number is not valid")
            else:
                new_data['phone_number'].append(f"+{str(df['phone_number'][i])[:12]}")
            new_data['created_at'].append(str(df['created_at'][i]))
        
        new_data = pd.DataFrame(new_data)
        now = datetime.now().strftime("%Y_%m_%d")
        new_data.to_excel(f'extras/users_data_{now}.xlsx', index=False)
        return f"extras/users_data_{now}.xlsx"

    except Exception as e:
        print(e)
        return None

async def get_registered_users():
    try:
        query = """
        SELECT user_id, user_fullname, phone_number, job, DATE(date) as date
        FROM user_poll
        """
        data = await fetch_query(query=query)
        if not data:
            return "Ma'lumot mavjud emas!"
        df = pd.DataFrame(data)

        df.columns = ['user_id', 'user_fullname', 'phone_number', 'job', 'date']

        now = datetime.now().strftime("%Y_%m_%d")
        df.to_excel(f'extras/registered_users_{now}.xlsx', index=False)
        return f"extras/registered_users_{now}.xlsx"

    except Exception as e:
        print(e)
        return None

polls = []


async def insert_data(poll_data, poll_ids, question):
    try:
        with open("polls/poll_data.json", "r") as file:
            data = json.load(file)
    except FileNotFoundError as e:
        print(e)


    try:
        with open("polls/poll_ids.json", "r") as file:
            polls_id = json.load(file)
    except FileNotFoundError as e:
        print(e)
    
    ids = {
        f"{question}" : poll_ids
    }
    
    data.update(poll_data)
    polls_id.update(ids)

    with open('polls/poll_data.json', "w") as file:
        json.dump(data, file, indent=4)
        print("New data added to [poll_data]")
    
    with open('polls/poll_ids.json', "w") as file:
        json.dump(polls_id, file, indent=4)
        print("New data added to [poll_data]")
    
    

async def change_data(id, new_data):
    with open('polls/poll_data.json', 'r') as file:
        data = json.load(file)

    data[id] = new_data

    with open('polls/poll_data.json', 'w') as file:
        json.dump(data, file, indent=4)
        print(f"Data changed to \n{new_data}")

async def get_result(name):
    with open('polls/poll_ids.json', 'r') as file:
        poll_ids = json.load(file)

    with open('polls/poll_data.json', 'r') as file:
        poll_data = json.load(file)
    
    main_question = ''
    result = {}
    for key, value in poll_data.items():
        if key in poll_ids[name]:
            if 'question' not in result:
                main_question = value['question']
                result['question'] = main_question
                for option, count in value.items():
                    if option == 'question':
                        continue
                    result[option] = count
            else:
                for option, count in value.items():
                    if option == 'question':
                        continue
                    if option in result:
                        result[option] += count
                    else:
                        result[option] = count

    return result

async def create_poll(received_question, received_options):
        

    data = {

    }

    poll_ids = []

    users = await fetch_query("SELECT user_id, name FROM users")
    cnt = 0
    for user in users:
        try:
            options = received_options
            question = received_question.replace("$name", user['name'])
            try:
                poll_message = await bot.send_poll(chat_id=user['user_id'],question=question, options=options)
                print(f"Poll sent to {user['name']} ({user['user_id']})")
                
            except Exception as e:
                if 'Forbidden' in str(e):
                    await execute_query(f"DELETE FROM users WHERE user_id = '{user['id']}';")
                print(e)
                continue

            ##############################
            poll_id = poll_message.poll.id
            poll_ids.append(poll_id)

            data[poll_id] = {}
            data[poll_id]['question'] = question

            for option in options:
                data[poll_id][option] = 0
            asyncio.sleep(0.05)
            cnt += 1

        except Exception as e:
            print(e)
            continue
    print(f"Polls sent to {cnt} users")
    await bot.send_message(chat_id=7102300410,text=f"{cnt} ta foydalanuvchiga so'rovnoma yuborildi✅")
    

    await insert_data(data, poll_ids, question)   

async def show_books():
    query = "SELECT * FROM books"
    books = await fetch_query(query)

    logging.info(f"Books: {books}")
    books_text = "Kitoblar ro'yxati:\n\n"
    for book in books:
        books_text += f"{book['book_name']} - {book['book_id']}: {book['book_location_link']}\n"
    return books_text

async def add_book(book_name, book_id, book_link):
    try:
        query = "INSERT INTO books (book_name, book_id, book_location_link) VALUES ($1, $2, $3);"
        await execute_query(query, (book_name, book_id, book_link))
        return "success"
    except Exception as e:
        logging.error(f"Error: {e}")
        return None
    
async def edit_book(book_id, new_book_name, new_book_link, new_book_id=0):
    if new_book_id == 0:
        try:
            query = "UPDATE books SET book_name = $1, book_location_link = $2 WHERE book_id = $3;"
            await execute_query(query, (new_book_name, new_book_link, book_id))
            return "success"
        except Exception as e:
            logging.error(f"Error: {e}")
            return None
    else:
        try:
            query = "UPDATE books SET book_id = $1, book_name = $2, book_location_link = $3 WHERE book_id = $4;"
            await execute_query(query, (new_book_id, new_book_name, new_book_link, book_id))
            return "success"
        except Exception as e:
            logging.error(f"Error: {e}")
            return None
        
async def delete_book(book_id):
    try:
        query = "DELETE FROM books WHERE book_id = $1;"
        await execute_query(query, (book_id,))
        return "success"
    except Exception as e:
        logging.error(f"Error: {e}")
        return None

async def get_statistic(user_id):
    query = "SELECT * FROM users;"
    users = await fetch_query(query)
    df = pd.DataFrame(users)
    df.columns = ['id', 'user_id', 'username', 'name', 'phone_number', 'created_at', 'updated_at', 'cur_msg_id', 'is_check', 'friends_count']
    # I need to create a new column as user_rank based on their the number of friends
    df['user_rank'] = df['friends_count'].rank(method='min', ascending=False).astype(int)

    sorted_df = df.sort_values(by="friends_count", ascending=False)
    sorted_df["user_rank"] = range(1, len(sorted_df) + 1)

    user_stat = sorted_df[sorted_df['user_id'] == user_id]
    user_stat = user_stat[['name', 'friends_count', 'user_rank']]
    user_stat = user_stat.to_dict('records')[0]

    top_10_users = sorted_df.head(10)
    top_10_users = top_10_users[['name', 'friends_count', 'user_rank']]
    top_10_users = top_10_users.to_dict('records')

    final_result = "🔰 Top 10 foydalanuvchilar 🔰\n\n"
    for user in top_10_users:
        final_result += f"{user['user_rank']}. {user['name']} - {user['friends_count']} ta do'stlar\n"
    
    final_result = final_result + f"\nSizning ma'lumotlaringiz:\n{user_stat['user_rank']}. {user_stat['name']} - {user_stat['friends_count']} ta do'stlar"
    return final_result



async def handle_start_message(message, state):
    print(message.text)
    special_data = message.text.split('/start ')[1] if '/start ' in message.text else None
    if special_data and special_data == 'all':
        await message.reply(f"Assalomu alekum, {message.from_user.first_name}. \nXush kelibsiz!\n\nQuyida barcha kitoblarni ko'rishingiz mumkin!", reply_markup=kb.main_menu_button)
        msg_url = await fetch_query(f"SELECT b.book_location_link FROM books b;")
        for msg in msg_url:
            pattern = r"https://t\.me/c/2343907878/(\d+)"
            match = re.match(pattern, msg['book_location_link'])
            if match:
                msg_id = int(match.group(1))
            
            if msg_id ==31:
                continue
            await bot.copy_message(chat_id=message.chat.id, from_chat_id=CHANNEL_ID, message_id=msg_id)
        user_data_query = f"INSERT INTO users (user_id, username, name, phone_number, created_at) VALUES ($1, $2, $3, $4, NOW()) ON CONFLICT (user_id) DO NOTHING;"
        await execute_query(user_data_query,(str(message.from_user.id), message.from_user.username, message.from_user.first_name, None))
    elif special_data:
        part_one, part_two = special_data.split('_')
        if part_one == "invite":
            user_exist = await fetch_query(f"SELECT user_id FROM users WHERE user_id = '{message.from_user.id}';")
            if user_exist:
                await message.reply(f"Assalomu alaykum, {message.from_user.first_name}. \nXush kelibsiz!", reply_markup=kb.main_menu_button)
                await bot.send_message(chat_id=part_two, text=f"{message.from_user.first_name} siz yuborgan link orqali tashrif buyurdi. Ammo u allaqachon botga tashrif buyurgan edi😔!")
                return

            user_data_query = f"INSERT INTO users (user_id, username, name, phone_number, created_at) VALUES ($1, $2, $3, $4, NOW()) ON CONFLICT (user_id) DO NOTHING;"
            await execute_query(user_data_query,(str(message.from_user.id), message.from_user.username, message.from_user.first_name, None))
            
            await execute_query(f"UPDATE users SET friends_count = friends_count + 1 WHERE user_id = '{part_two}';")
            try:
                increase_friend_count = f"UPDATE users SET friends_count = friends_count + 1 WHERE user_id = '{part_two}';"
                await execute_query(increase_friend_count)
            except:
                pass

            await bot.send_message(chat_id=part_two, text=f"👤{message.from_user.first_name} siz yuborgan link orqali tashrif buyurdi.")
            await message.reply(f"Assalomu alaykum, xush kelibsiz {message.from_user.first_name}!\nIltimos quyidagi bir qancha savollarga javob berishingizni so'raymiz!")
            await message.answer("Iltimos, ismingizni kiriting:")
            await state.set_state(WelcomePoll.user_fullname)
            return
        else:
            phone_number, book_id = part_one, part_two
            print(phone_number, book_id)
            query = f"SELECT start_msg_id, links FROM start_messages WHERE start_msg_id = '{book_id}';"
            messages = await fetch_query(query)
            print(messages)
            links = json.loads(messages[0]['links'])
            with open('extras/messages.json', 'r') as file:
                data = json.load(file)

                for link in links:
                    try:
                        if link.startswith("$start_msg"):
                            # Use local message.
                            message_key = link[1:]
                            if message_key not in data:
                                logging.error(f"No local message found for key '{message_key}'")
                                continue
                            else:
                                book_name = await fetch_query(f"SELECT book_name FROM books WHERE book_id = '{book_id}';")
                                logging.info(f"Book name: {book_name}")
                                message_text = data[message_key]
                                personalized_text = message_text.replace("$name", message.from_user.first_name).replace("$book_name", book_name[0]['book_name'])
                                await bot.send_message(message.chat.id, personalized_text, disable_web_page_preview=True)
                        else:
                            message_id_extracted = await extract_message_id(link)
                            if not message_id_extracted:
                                logging.error(f"Failed to extract message id from link: {link}")
                                continue
                            await bot.copy_message(message.chat.id, CHANNEL_ID, message_id_extracted)
                    except Exception as e:
                        logging.error(f"Error sending message for user with link {link}: {e}")


            user_data_query = f"INSERT INTO users (user_id, username, name, phone_number, created_at) VALUES ($1, $2, $3, $4, NOW()) ON CONFLICT (user_id) DO NOTHING;"
            await execute_query(user_data_query,(str(message.from_user.id), message.from_user.username, message.from_user.first_name, phone_number))

    else:
        await message.reply(f"Assalomu alekum, {message.from_user.first_name}. \nXush kelibsiz!", reply_markup=kb.main_menu_button)

        user_data_query = f"INSERT INTO users (user_id, username, name, phone_number, created_at) VALUES ($1, $2, $3, $4, NOW()) ON CONFLICT (user_id) DO NOTHING;"
        await execute_query(user_data_query,(str(message.from_user.id), message.from_user.username, message.from_user.first_name, None))