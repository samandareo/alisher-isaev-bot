from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    message_text_id = State()
    message_text = State()

class AdminState(StatesGroup):
    admin_action = State()
    send_type_message = State()
    copy_type_message = State()

class AdminStateOne(StatesGroup):
    userOneId = State()
    admin_action = State()
    send_type_message = State()
    copy_type_message = State()
    copy_message_text = State()
    message_text = State()

class UserMessagesToAdmin(StatesGroup):
    message_text = State()
    message_proove = State()

class CreatePoll(StatesGroup):
    question = State()
    count = State()
    option = State()
    proove = State()
    
class PollResults(StatesGroup):
    poll_name = State()


class ChangeBooks(StatesGroup):
    choose_action = State()
    book_name = State()
    book_id = State()
    book_link = State()
    book_id_delete = State()
    book_id_edit = State()
    book_name_edit = State()
    book_link_edit = State()
    new_book_id_proove = State()
    book_new_id_edit = State()

class WelcomePoll(StatesGroup):
    user_fullname = State()
    user_phone = State()
    user_job = State()
    referred_by = State()

class WebinarPoll(StatesGroup):
    user_fullname = State()
    user_phone = State()
    user_job = State()
    referred_by = State()