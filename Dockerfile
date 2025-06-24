FROM python:3.9-slim

WORKDIR /app

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов
COPY requirements.txt .
COPY . .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Запуск бота
CMD ["python", "main.py"]