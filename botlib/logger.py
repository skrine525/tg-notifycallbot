import logging, aiogram
from logging.handlers import TimedRotatingFileHandler
from botlib.paths import log_file

# Настройка логирования
formatter = logging.Formatter('[%(asctime)s] [%(filename)s:%(lineno)d %(threadName)s] [%(name)s] [%(levelname)s] - %(message)s')
file_handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=14, encoding='utf-8')
file_handler.setFormatter(formatter)

# Меняем логер aiogram
aiogram_logger = logging.getLogger('aiogram')
aiogram_logger.handlers = [file_handler]
aiogram_logger.setLevel(logging.INFO)