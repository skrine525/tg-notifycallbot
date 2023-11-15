import pyrogram, sqlalchemy.exc
from aiogram import types
from sqlalchemy import update
from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from botlib.db.model import User, ListeningChannel, NotifiedUser
from pyrogram.errors.exceptions.bad_request_400 import UsernameNotOccupied, UsernameInvalid
from botlib.db.engine import Session
from botlib.user import user_client
from botlib import decorators


# Команды и Callback
admin_command = Command("admin")
admin_cb = CallbackData("admin", "action")
manage_channels_cb = CallbackData("manager_channels", "type")
add_channel_cb = CallbackData("add_channel", 'tg_chat_id')
manage_channel_cb = CallbackData("manage_channel", "type", "listening_channel_id")
add_user_cb = CallbackData("add_user", "listening_channel_id", "tg_user_id")
remove_user_cb = CallbackData("remove_user", "type", "notified_user_id")

# Состояния добавления пользователя
class AddUserStates(StatesGroup):
    get_username = State()

@decorators.check_admin_in_handler
async def admin_message_handler(message: types.Message, state: FSMContext):
    await state.finish()
    
    # Смотрим статус бота
    enabled = True
    with Session() as session:
        listening_channels = session.query(ListeningChannel).all()
        for listening_channel in listening_channels:
            if not listening_channel.enabled:
                enabled = False
                break
    
    if enabled:
        enabled_button_text = "Отключить бота"
        enabled_action = "disable"
        status_text = "Включен"
    else:
        enabled_button_text = "Включить бота"
        enabled_action = "enable"
        status_text = "Отключен"
            
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        enabled_button_text,
        callback_data=admin_cb.new(action=enabled_action)
    ))
    markup.add(types.InlineKeyboardButton(
        "Управление каналами",
        callback_data=manage_channels_cb.new(type="main")
    ))
    
    text = f"Админ меню.\n\nСтатус бота: <b>{status_text}</b>"
    await message.reply(text, reply_markup=markup)

@decorators.check_admin_in_handler
async def admin_query_handler(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await state.finish()
    
    action = callback_data["action"]
    
    if action == "enable":
        with Session() as session:
            stmt = update(ListeningChannel).values(enabled=True)
            session.execute(stmt)
            session.commit()
            enabled = True
    elif action == "disable":
        with Session() as session:
            stmt = update(ListeningChannel).values(enabled=False)
            session.execute(stmt)
            session.commit()
            enabled = False
    else:
        # Смотрим статус бота
        enabled = True
        with Session() as session:
            listening_channels = session.query(ListeningChannel).all()
            for listening_channel in listening_channels:
                if not listening_channel.enabled:
                    enabled = False
                    break
        
    if enabled:
        enabled_button_text = "Отключить бота"
        enabled_action = "disable"
        status_text = "Включен"
    else:
        enabled_button_text = "Включить бота"
        enabled_action = "enable"
        status_text = "Отключен"
            
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        enabled_button_text,
        callback_data=admin_cb.new(action=enabled_action)
    ))
    markup.add(types.InlineKeyboardButton(
        "Управление каналами",
        callback_data=manage_channels_cb.new(type="main")
    ))
    
    text = f"Админ меню.\n\nСтатус бота: <b>{status_text}</b>"
    await query.message.edit_text(text, reply_markup=markup)

@decorators.check_admin_in_handler
async def manage_channels_query_handler(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await state.finish()
    
    if callback_data["type"] == "main":
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "Добавить канал",
            callback_data=manage_channels_cb.new(type="add_show")
        ))
        markup.add(types.InlineKeyboardButton(
            "Управлять каналом",
            callback_data=manage_channels_cb.new(type="manage_show")
        ))
        markup.add(types.InlineKeyboardButton(
            "« Назад",
            callback_data=admin_cb.new(action="")
        ))
        
        with Session() as session:
            listening_channels = session.query(ListeningChannel).all()
        
        if len(listening_channels) > 0:
            channels_to_print_list = []
            for listening_channel in listening_channels:
                status_text = "✅" if listening_channel.enabled else "⛔️"
                channels_to_print_list.append(f"{status_text} {listening_channel.title}")
            channel_list_text = '\n'.join(channels_to_print_list)
        else:
            channel_list_text = "Пусто"
        
        await query.message.edit_text(f"Управление каналами.\n\nСписок активных каналов:\n{channel_list_text}", reply_markup=markup)
    elif callback_data["type"] == "add_show":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "« Назад",
            callback_data=manage_channels_cb.new(type="main")
        ))
        
        dialogs = [x async for x in user_client.get_dialogs()]
        
        with Session() as session:
            listening_channels = session.query(ListeningChannel).all()
        
        listening_chat_ids = [listening_channel.tg_chat_id for listening_channel in listening_channels]
        for dialog in dialogs:
            if not dialog.is_pinned and dialog.chat.type == pyrogram.enums.ChatType.CHANNEL and not dialog.chat.id in listening_chat_ids:
                markup.add(types.InlineKeyboardButton(
                    dialog.chat.title,
                    callback_data=add_channel_cb.new(tg_chat_id=dialog.chat.id)
                ))
        
        await query.message.edit_text(f"Выберите канал, который хотите добавить.", reply_markup=markup)
    elif callback_data["type"] == "manage_show":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "« Назад",
            callback_data=manage_channels_cb.new(type="main")
        ))
        
        with Session() as session:
            listening_channels = session.query(ListeningChannel).all()
            
        for listening_channel in listening_channels:
            markup.add(types.InlineKeyboardButton(
                listening_channel.title,
                callback_data=manage_channel_cb.new(type="main", listening_channel_id=listening_channel.listening_channel_id)
            ))
        
        await query.message.edit_text(f"Выберите канал, которым хотите управлять.", reply_markup=markup)

@decorators.check_admin_in_handler 
async def add_channel_query_handler(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await state.finish()
    
    tg_chat_id = callback_data["tg_chat_id"]
    chat = await user_client.get_chat(tg_chat_id)
    title = chat.title
    
    try:
        with Session() as session:
            listening_channel = session.query(ListeningChannel).filter_by(tg_chat_id=tg_chat_id)
            
            listening_channel = ListeningChannel(tg_chat_id, title)
            session.add(listening_channel)
            session.commit()
            
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "« Назад",
            callback_data=manage_channels_cb.new(type="add_show")
        ))
            
        await query.message.edit_text(f"Канал <u>{title}</u> успешно добавлен.", reply_markup=markup)
    except sqlalchemy.exc.IntegrityError as e:
        await query.answer("⛔️ Не удалось добавить канал.")

@decorators.check_admin_in_handler
async def manage_channel_query_handler(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await state.finish()
    
    type = callback_data["type"]
    listening_channel_id = callback_data['listening_channel_id']
    
    with Session() as session:
        listening_channel = session.query(ListeningChannel).filter_by(listening_channel_id=listening_channel_id).first()
        
        if listening_channel:
            if type == "main":
                markup = types.InlineKeyboardMarkup()
                enabled_text = "Отключить прослушивание" if listening_channel.enabled else "Включить прослушивание"
                markup.add(types.InlineKeyboardButton(
                    enabled_text,
                    callback_data=manage_channel_cb.new(type="change_enabled", listening_channel_id=listening_channel.listening_channel_id)
                ))
                markup.add(
                    types.InlineKeyboardButton(
                    "Добавить пользователя",
                    callback_data=manage_channel_cb.new(type="add_user", listening_channel_id=listening_channel.listening_channel_id)
                ))
                markup.add(
                    types.InlineKeyboardButton(
                        "Удалить пользователя",
                        callback_data=manage_channel_cb.new(type="remove_user", listening_channel_id=listening_channel.listening_channel_id)
                ))
                markup.add(types.InlineKeyboardButton(
                    "Удалить канал",
                    callback_data=manage_channel_cb.new(type="delete", listening_channel_id=listening_channel.listening_channel_id)
                ))
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channels_cb.new(type="manage_show")
                ))
                
                status_text = "Включен" if listening_channel.enabled else "Отключен"
                user_count = len(listening_channel.notified_users)
                text = f"Управление каналом.\n\nКанал: <u>{listening_channel.title}</u>\nСтатус: <b>{status_text}</b>\n<i>Пользователей</i>: {user_count}"
                await query.message.edit_text(text, reply_markup=markup)
            elif type == "change_enabled":
                listening_channel.enabled = not listening_channel.enabled
                session.commit()
                
                markup = types.InlineKeyboardMarkup()
                enabled_text = "Отключить прослушивание" if listening_channel.enabled else "Включить прослушивание"
                markup.add(types.InlineKeyboardButton(
                    enabled_text,
                    callback_data=manage_channel_cb.new(type="change_enabled", listening_channel_id=listening_channel.listening_channel_id)
                ))
                markup.add(
                    types.InlineKeyboardButton(
                    "Добавить пользователя",
                    callback_data=manage_channel_cb.new(type="add_user", listening_channel_id=listening_channel.listening_channel_id)
                ))
                markup.add(
                    types.InlineKeyboardButton(
                        "Удалить пользователя",
                        callback_data=manage_channel_cb.new(type="remove_user", listening_channel_id=listening_channel.listening_channel_id)
                ))
                markup.add(types.InlineKeyboardButton(
                    "Удалить канал",
                    callback_data=manage_channel_cb.new(type="delete", listening_channel_id=listening_channel.listening_channel_id)
                ))
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channels_cb.new(type="manage_show")
                ))
                
                status_text = "Включен" if listening_channel.enabled else "Отключен"
                user_count = len(listening_channel.notified_users)
                text = f"Управление каналом.\n\nКанал: <u>{listening_channel.title}</u>\nСтатус: <b>{status_text}</b>\n<i>Пользователей</i>: {user_count}"
                await query.message.edit_text(text, reply_markup=markup)
            elif type == "delete":
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(
                    "Подтвердить",
                    callback_data=manage_channel_cb.new(type="delete_confirm", listening_channel_id=listening_channel.listening_channel_id)
                ))
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channel_cb.new(type="main", listening_channel_id=listening_channel.listening_channel_id)
                ))
                
                text = f"Вы уверены, что хотите удалить канал <u>{listening_channel.title}</u>?"
                await query.message.edit_text(text, reply_markup=markup)
            elif type == "delete_confirm":
                session.delete(listening_channel)
                session.commit()
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channels_cb.new(type="manage_show")
                ))
                
                text = f"Канал <u>{listening_channel.title}</u> успешно удален."
                await query.message.edit_text(text, reply_markup=markup)
            elif type == "add_user":
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channel_cb.new(type="main", listening_channel_id=listening_channel.listening_channel_id)
                ))
                
                await AddUserStates.first()
                async with state.proxy() as state_data:
                    state_data["listening_channel_id"] = listening_channel_id
                    state_data["menu_message_id"] = query.message.message_id
                
                text = f"Введите username пользователя, которого хотите добавить в канал <u>{listening_channel.title}</u>."
                await query.message.edit_text(text, reply_markup=markup)
            elif type == "remove_user":
                notified_users_query = session.query(NotifiedUser, User)
                notified_users_query = notified_users_query.join(NotifiedUser, User.user_id == NotifiedUser.user_id, isouter=False)
                notified_users_query = notified_users_query.filter_by(listening_channel_id=listening_channel_id)
                notified_users = notified_users_query.all()
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channel_cb.new(type="main", listening_channel_id=listening_channel.listening_channel_id)
                ))
                
                for notified_user, user in notified_users:
                    markup.add(types.InlineKeyboardButton(
                        user.name,
                        callback_data=remove_user_cb.new(type="main", notified_user_id=notified_user.notified_user_id)
                    ))
                    
                text = "Выберите пользователя, которого хотите удалить из канала."
                await query.message.edit_text(text, reply_markup=markup)
        else:
            await query.answer("⛔️ Ошибка: Канал не добавлен.")

@decorators.check_admin_in_handler           
async def get_username(message: types.Message, state: FSMContext):
    async with state.proxy() as state_data:
        listening_channel_id = state_data["listening_channel_id"]
        menu_message_id = state_data["menu_message_id"]
    
    try:
        user_chat = await user_client.get_chat(message.text)
        if user_chat.type == pyrogram.enums.ChatType.PRIVATE:
            await state.finish()
            
            with Session() as session:
                user = session.query(User).filter_by(tg_user_id=user_chat.id).first()
                
                if user:
                    notified_user = session.query(NotifiedUser).filter_by(listening_channel_id=listening_channel_id, user_id=user.user_id).first()
                else:
                    notified_user = None
                    
            if notified_user:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(
                    "Указать снова",
                    callback_data=manage_channel_cb.new(type="add_user", listening_channel_id=listening_channel_id)
                ))
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channel_cb.new(type="main", listening_channel_id=listening_channel_id)
                ))
                
                if user_chat.last_name:
                    fullname = f"{user_chat.first_name} {user_chat.last_name}"
                else:
                    fullname = user_chat.first_name
                    
                listening_channel = session.query(ListeningChannel).filter_by(listening_channel_id=listening_channel_id).first()
                
                text = f"Пользователь <u>{fullname}</u> уже добавлен в канал <u>{listening_channel.title}</u>."
                await message.bot.delete_message(message.chat.id, message.message_id)
                await message.bot.edit_message_text(text, message.chat.id, menu_message_id, reply_markup=markup)
            else:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(
                    "Добавить в канал",
                    callback_data=add_user_cb.new(listening_channel_id=listening_channel_id, tg_user_id=user_chat.id)
                ))
                markup.add(types.InlineKeyboardButton(
                    "Указать снова",
                    callback_data=manage_channel_cb.new(type="add_user", listening_channel_id=listening_channel_id)
                ))
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channel_cb.new(type="main", listening_channel_id=listening_channel_id)
                ))
                
                if user_chat.last_name:
                    fullname = f"{user_chat.first_name} {user_chat.last_name}"
                else:
                    fullname = user_chat.first_name
                    
                listening_channel = session.query(ListeningChannel).filter_by(listening_channel_id=listening_channel_id).first()
                    
                text = f"Добавить пользователя <u>{fullname}</u> в канал <u>{listening_channel.title}</u>"
                await message.bot.delete_message(message.chat.id, message.message_id)
                await message.bot.edit_message_text(text, message.chat.id, menu_message_id, reply_markup=markup)
        else:
            await message.bot.delete_message(message.chat.id, message.message_id)
    except UsernameNotOccupied:
        await state.finish()
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "Указать снова",
            callback_data=manage_channel_cb.new(type="add_user", listening_channel_id=listening_channel_id)
        ))
        markup.add(types.InlineKeyboardButton(
            "« Назад",
            callback_data=manage_channel_cb.new(type="main", listening_channel_id=listening_channel_id)
        ))
        
        text = "Пользователь с указанным username не найден."
        await message.bot.delete_message(message.chat.id, message.message_id)
        await message.bot.edit_message_text(text, message.chat.id, menu_message_id, reply_markup=markup)
    except:
        await message.bot.delete_message(message.chat.id, message.message_id)

@decorators.check_admin_in_handler      
async def add_user_query_handler(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await state.finish()
    
    listening_channel_id = callback_data["listening_channel_id"]
    tg_user_id = callback_data["tg_user_id"]
    
    with Session() as session:
        try:
            user = session.query(User).filter_by(tg_user_id=tg_user_id).first()
            
            if not user:
                user_chat = await user_client.get_chat(tg_user_id)
                if user_chat.last_name:
                    fullname = f"{user_chat.first_name} {user_chat.last_name}"
                else:
                    fullname = user_chat.first_name
                user = User(tg_user_id, fullname)
                
                session.add(user)
                session.commit()
                
            notified_user = session.query(NotifiedUser).filter_by(user_id=user.user_id, listening_channel_id=listening_channel_id).first()
            
            if notified_user:
                await query.answer("⛔️ Ошибка: Пользователь уже добавлен.")
            else:
                notified_user = NotifiedUser(user.user_id, listening_channel_id)
                session.add(notified_user)
                session.commit()
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channel_cb.new(type="main", listening_channel_id=listening_channel_id)
                ))
                
                listening_channel = session.query(ListeningChannel).filter_by(listening_channel_id=listening_channel_id).first()
                
                text = f"Пользователь <u>{user.name}</u> успешно добавлен в канал <u>{listening_channel.title}</u>."
                await query.message.edit_text(text, reply_markup=markup)
        except (UsernameInvalid, UsernameNotOccupied):
            await query.answer("⛔️ Ошибка: Не удалось получить данные пользователя.")

@decorators.check_admin_in_handler            
async def remove_user_query_handler(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await state.finish()
    
    type = callback_data["type"]
    notified_user_id = callback_data["notified_user_id"]
    
    if type == 'main':
        with Session() as session:
            markup = types.InlineKeyboardMarkup()
            try:
                notified_user, user, listening_channel = (
                    session.query(NotifiedUser, User, ListeningChannel)
                    .join(User, NotifiedUser.user_id == User.user_id, isouter=False)
                    .join(ListeningChannel, NotifiedUser.listening_channel_id == ListeningChannel.listening_channel_id, isouter=False)
                    .filter(NotifiedUser.notified_user_id == notified_user_id)
                    .first()
                )
                
                markup.add(types.InlineKeyboardButton(
                    "Подтвердить",
                    callback_data=remove_user_cb.new(type="confirm", notified_user_id=notified_user_id)
                ))
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channel_cb.new(type="remove_user", listening_channel_id=notified_user.listening_channel_id)
                ))
                text = f"Удалить пользователя <u>{user.name}</u> из канала <u>{listening_channel.title}</u>?"
            except TypeError:
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channels_cb.new(type="main")
                ))
                text = f"⛔️ Ошибка: Пользователь не найден. Возможно пользователь уже удален."
            
            await query.message.edit_text(text, reply_markup=markup)
    elif type == 'confirm':
        with Session() as session:
            markup = types.InlineKeyboardMarkup()
            try:
                notified_user, user, listening_channel = (
                    session.query(NotifiedUser, User, ListeningChannel)
                    .join(User, NotifiedUser.user_id == User.user_id, isouter=False)
                    .join(ListeningChannel, NotifiedUser.listening_channel_id == ListeningChannel.listening_channel_id, isouter=False)
                    .filter(NotifiedUser.notified_user_id == notified_user_id)
                    .first()
                )
        
                session.delete(notified_user)
                session.commit()
                
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channel_cb.new(type="remove_user", listening_channel_id=notified_user.listening_channel_id)
                ))
                text = f"Пользователь <u>{user.name}</u> успешно удален из канала <u>{listening_channel.title}</u>."
            except TypeError:
                markup.add(types.InlineKeyboardButton(
                    "« Назад",
                    callback_data=manage_channels_cb.new(type="main")
                ))
                text = f"⛔️ Ошибка: Пользователь не найден. Возможно пользователь уже удален."
                
            await query.message.edit_text(text, reply_markup=markup)
