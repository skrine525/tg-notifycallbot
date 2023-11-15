from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher.filters import Command
from botlib.db.model import User, ListeningChannel, NotifiedUser
from botlib.db.engine import Session

start_command = Command("start")
menu_command = Command("menu")
menu_cb = CallbackData("menu")
manage_notifications_cb = CallbackData("manage_notifications")
manage_notification_cb = CallbackData("manage_notification", "notified_user_id", "action")

async def menu_message_handler(message: types.Message, state: FSMContext):
    state.finish()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "Управление уведомлениями",
        callback_data=manage_notifications_cb.new()
    ))
    
    await message.reply("Меню.", reply_markup=markup)
    
async def menu_query_handler(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await state.finish()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "Управление уведомлениями",
        callback_data=manage_notifications_cb.new()
    ))
    
    await query.message.edit_text("Меню.", reply_markup=markup)
    
async def manage_notifications_query_handler(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await state.finish()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "« Назад",
        callback_data=menu_cb.new()
    ))
    
    with Session() as session:
        try:
            text = "Выберите канал, для управления уведомлениями."
            query_result = (
                session.query(NotifiedUser, User, ListeningChannel)
                .join(User, NotifiedUser.user_id == User.user_id, isouter=False)
                .join(ListeningChannel, NotifiedUser.listening_channel_id == ListeningChannel.listening_channel_id, isouter=False)
                .filter(User.tg_user_id == query.from_user.id)
                .all()
            )
            
            for notified_user, user, listening_channel in query_result:
                markup.add(types.InlineKeyboardButton(
                    listening_channel.title,
                    callback_data=manage_notification_cb.new(notified_user_id=notified_user.notified_user_id, action="")
                ))
        except TypeError:
            text = "⛔️ Ошибка: Не удалось получить список каналов."
            
    await query.message.edit_text(text, reply_markup=markup)
    
async def manage_notification_query_handler(query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await state.finish()
    
    notified_user_id = callback_data["notified_user_id"]
    action = callback_data["action"]
    
    markup = types.InlineKeyboardMarkup()
    
    with Session() as session:
        try:
            notified_user, listening_channel = (
                session.query(NotifiedUser, ListeningChannel)
                .join(ListeningChannel, NotifiedUser.listening_channel_id == ListeningChannel.listening_channel_id, isouter=False)
                .filter(NotifiedUser.notified_user_id == notified_user_id)
                .first()
            )
            
            if action == "enable":
                notified_user.notifications_enabled = True
                session.commit()
            elif action == "disable":
                notified_user.notifications_enabled = False
                session.commit()
            
            if notified_user.notifications_enabled:
                status_text = "Включены"
                enable_button_text = "Отключить уведомления"
                enable_action = "disable"
            else:
                status_text = "Отключены"
                enable_button_text = "Включить уведомления"
                enable_action = "enable"
            
            markup.add(types.InlineKeyboardButton(
                enable_button_text,
                callback_data=manage_notification_cb.new(notified_user_id=notified_user_id, action=enable_action)
            ))
            markup.add(types.InlineKeyboardButton(
                "« Назад",
                callback_data=manage_notifications_cb.new()
            ))
            
            text = f"Канал: <u>{listening_channel.title}</u>\nУведомления: <b>{status_text}</b>"
        except TypeError:
            text = "⛔️ Ошибка: Не удалось получить данные о канале."
            markup.add(types.InlineKeyboardButton(
                "« Назад",
                callback_data=manage_notifications_cb.new()
            ))
    
    await query.message.edit_text(text, reply_markup=markup)