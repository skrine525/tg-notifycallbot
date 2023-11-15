import asyncio, threading, logging
from logging.handlers import TimedRotatingFileHandler
from aiogram.utils import executor
from botlib.paths import log_file
from botlib.dispatcher import dp, set_menu_commands
from botlib.db.engine import engine
from botlib.db.model import Base
from botlib.user import user_client


# Настройка логирования
formatter = logging.Formatter('[%(asctime)s] [%(filename)s:%(lineno)d %(threadName)s] [%(name)s] [%(levelname)s] - %(message)s')
file_handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=14, encoding='utf-8')
file_handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[file_handler])

# Процедура потока бота
def bot_thread_handler():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(set_menu_commands())
    executor.start_polling(dp, skip_updates=True)
        
# Запуск бота
if __name__ == '__main__':        
    # Создаем таблицы БД
    Base.metadata.create_all(engine)
    
    # Создаем и запускаем поток бота
    bot_therad = threading.Thread(target=bot_thread_handler, daemon=True)
    bot_therad.start()
    
    # Запускаем польщовательский клиент в основном потоке
    user_client.run()
    