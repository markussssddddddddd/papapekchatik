# Телеграм бот для пекарни

Бот для заказа пирогов с возможностью просмотра меню, акций и оформления заказов.

## Установка и запуск

1. Клонируйте репозиторий
2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл .env и добавьте в него токен вашего бота:
```
BOT_TOKEN=your_bot_token_here
```

4. Инициализируйте базу данных:
```bash
python init_db.py
```

5. Запустите бота:
```bash
python main.py
```

## Запуск через Docker

1. Соберите образ:
```bash
docker build -t bakery-bot .
```

2. Запустите контейнер:
```bash
docker run -d --name bakery-bot -e BOT_TOKEN=your_bot_token_here bakery-bot
```

## Функциональность

- Просмотр меню с категориями пирогов
- Специальные предложения
- Корзина для заказов
- Информация о доставке
- Информация о пекарне

## Управление администраторами

Для управления администраторами используйте скрипт `admin_manager.py`. Доступны следующие команды:

### Добавление администратора
```bash
python3 admin_manager.py add <user_id> <username>
```
Пример:
```bash
python3 admin_manager.py add 123456789 Ivan
```

### Удаление администратора
```bash
python3 admin_manager.py remove <user_id>
```
Пример:
```bash
python3 admin_manager.py remove 123456789
```

### Активация/деактивация администратора
```bash
python3 admin_manager.py toggle <user_id>
```
Пример:
```bash
python3 admin_manager.py toggle 123456789
```

### Просмотр списка администраторов
```bash
python3 admin_manager.py list
```

### Получение справки
```bash
python3 admin_manager.py --help
```

### Права администратора
Администраторы имеют доступ к дополнительным функциям:
- Просмотр всех оформленных заказов
- Просмотр всех активных корзин пользователей

Для получения ID пользователя в Telegram:
1. Попросите пользователя написать боту @userinfobot
2. Или используйте команду /start в вашем боте и посмотрите ID в логах 