import config
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, ParseMode
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from botlib.ui import admin as adminui
from botlib.ui import user as userui


# Установка токена бота и создание объектов Bot и Dispatcher
bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())

# Команды пользователя
dp.register_message_handler(userui.menu_message_handler, userui.start_command, state="*")
dp.register_message_handler(userui.menu_message_handler, userui.menu_command, state="*")
dp.register_callback_query_handler(userui.menu_query_handler, userui.menu_cb.filter(), state="*")
dp.register_callback_query_handler(userui.manage_notifications_query_handler, userui.manage_notifications_cb.filter(), state="*")
dp.register_callback_query_handler(userui.manage_notification_query_handler, userui.manage_notification_cb.filter(), state="*")

# Команды админа
dp.register_message_handler(adminui.admin_message_handler, adminui.admin_command, state="*")
dp.register_message_handler(adminui.get_username, content_types=['text'], state=adminui.AddUserStates.get_username)
dp.register_callback_query_handler(adminui.manage_channels_query_handler, adminui.manage_channels_cb.filter(), state="*")
dp.register_callback_query_handler(adminui.admin_query_handler, adminui.admin_cb.filter(), state="*")
dp.register_callback_query_handler(adminui.add_channel_query_handler, adminui.add_channel_cb.filter(), state="*")
dp.register_callback_query_handler(adminui.manage_channel_query_handler, adminui.manage_channel_cb.filter(), state="*")
dp.register_callback_query_handler(adminui.add_user_query_handler, adminui.add_user_cb.filter(), state="*")
dp.register_callback_query_handler(adminui.remove_user_query_handler, adminui.remove_user_cb.filter(), state="*")

# Корутина для установки команд в меню бота из menu_commands.json
async def set_menu_commands():
    bot_commands = [
        BotCommand("menu", "Меню бота")
    ]
    
    await bot.set_my_commands(bot_commands)