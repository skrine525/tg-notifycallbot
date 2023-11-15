import config
from aiogram import types
from functools import wraps


# Переменные
access_error_message = "⛔️ Ошибка: У вас нет доступа."                      # Переменная текста ошибки доступа

# Декоратор контроля доступа к обработчикам
def check_admin_in_handler(handler):
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        if isinstance(args[0], types.Message):
            if args[0].from_id in config.ADMIN_IDS:
                await handler(*args, **kwargs)
            else:
                await args[0].reply(access_error_message)
        elif isinstance(args[0], types.CallbackQuery):
            if args[0].from_user.id in config.ADMIN_IDS:
                await handler(*args, **kwargs)
            else:
                await args[0].answer(access_error_message)
    return wrapper