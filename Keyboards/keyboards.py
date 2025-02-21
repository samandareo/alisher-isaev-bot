from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_menu_button = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Murojaat")
        ],
        [
            KeyboardButton(text="📊Statistika"),
            KeyboardButton(text="🤝Do'stlarni taklif qilish")
        ]
    ],
    resize_keyboard=True
)

proove_message = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Ha", callback_data="proove"),
            InlineKeyboardButton(text="Yo'q", callback_data="cancel")
        ]
    ],
    resize_keyboard=True
)

proove_poll = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Ha", callback_data="proove"),
            InlineKeyboardButton(text="Yo'q", callback_data="cancel")
        ]
    ]
)

change_books = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Qo'shish", callback_data="add_book"),
            InlineKeyboardButton(text="O'chirish", callback_data="remove_book")
        ],
        [
            InlineKeyboardButton(text="Tahrirlash", callback_data="edit_book")
        ],
        [
            InlineKeyboardButton(text="Bekor qilish", callback_data="cancel")
        ]
    ]
)

book_id_proove = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Ha", callback_data="yes_change"),
            InlineKeyboardButton(text="Yo'q", callback_data="no_change")
        ]
    ]
)


send_to_friends = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Do'stlarga yuborish", switch_inline_query="")
        ]
    ]
)

request_phone_number = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Telefon raqamini yuborish", request_contact=True)
        ]
    ],
    resize_keyboard=True
)

user_jobs = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Tadbirkor", callback_data="tadbirkor"),
            InlineKeyboardButton(text="O'qituvchi", callback_data="oqituvchi"),
        ],
        [
            InlineKeyboardButton(text="Quruvchi", callback_data="quruvchi"),
            InlineKeyboardButton(text="Shafyor", callback_data="shafyor"),
        ],
        [
            InlineKeyboardButton(text="Boshqa", callback_data="boshqa")
        ]
    ]
)

send_message_type = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="SEND", callback_data="send_type_message"),
            InlineKeyboardButton(text="COPY", callback_data="send_type_copy")
        ]
    ]
)