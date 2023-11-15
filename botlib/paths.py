import os


# Переменные
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))               # Путь к корневой папке приложения
logs_dir = os.path.join(app_dir, "logs")                                            # Путь к папке с логам
database_file = os.path.join(app_dir, "database.db")                                # Путь к файлу SQLite3
config_file = os.path.join(app_dir, 'config.json')                                  # Путь к конфигурационному файлу
log_file  = os.path.join(logs_dir, 'bot.log')                                       # Путь к файлу логов

# Функция генерации директорий
def create_dirs():
    for key in globals().keys():
        if key.endswith("dir"):
            dir = globals()[key]
            if not os.path.exists(dir):
                os.mkdir(dir)
            
create_dirs()       # Создаем директории