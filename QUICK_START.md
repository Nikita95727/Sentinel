# 🚀 Быстрый старт Sentinel Bot

## Простой запуск в 2 шага

### 1. Развертывание (первый раз)

```bash
./deploy.sh
```

Это установит все зависимости и настроит проект.

### 2. Запуск бота

```bash
./start.sh
```

Готово! Бот запущен в фоне.

---

## Управление ботом

### Запуск
```bash
./start.sh
```

### Остановка
```bash
./stop.sh
```

### Проверка статуса
```bash
./status.sh
```

### Просмотр логов
```bash
# Последний лог файл
tail -f logs/bot_*.log

# Или все логи
tail -f logs/sentinel_*.log
```

---

## Что делают скрипты

### `deploy.sh` - Развертывание
- ✅ Проверяет Python и зависимости
- ✅ Создает виртуальное окружение
- ✅ Устанавливает пакеты
- ✅ Настраивает конфигурацию
- ✅ Опционально создает systemd service

### `start.sh` - Запуск
- ✅ Проверяет что все готово
- ✅ Запускает бота в фоне
- ✅ Сохраняет PID для управления
- ✅ Создает лог файл

### `stop.sh` - Остановка
- ✅ Graceful shutdown (корректная остановка)
- ✅ Принудительная остановка при необходимости
- ✅ Удаляет PID файл

### `status.sh` - Статус
- ✅ Показывает запущен ли бот
- ✅ Время работы
- ✅ Использование ресурсов (CPU, RAM)
- ✅ Последние строки лога

---

## Примеры использования

### Первый запуск на VPS

```bash
# 1. Клонировать проект (если нужно)
git clone <repo-url> Sentinel
cd Sentinel

# 2. Развернуть
./deploy.sh

# 3. Настроить .env (добавить API ключи)
nano .env

# 4. Запустить
./start.sh

# 5. Проверить статус
./status.sh
```

### Ежедневное использование

```bash
# Утром - проверить статус
./status.sh

# Если нужно перезапустить
./stop.sh
./start.sh

# Посмотреть логи
tail -f logs/bot_*.log
```

### Обновление проекта

```bash
# Обновить код
git pull

# Обновить зависимости (если нужно)
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Перезапустить
./stop.sh
./start.sh
```

---

## Troubleshooting

### Бот не запускается

```bash
# Проверить логи
tail -20 logs/bot_*.log

# Проверить что .env настроен
cat .env

# Проверить что venv существует
ls -la venv/

# Переустановить зависимости
source venv/bin/activate
pip install -r requirements.txt
```

### Бот запущен но не работает

```bash
# Проверить статус
./status.sh

# Посмотреть последние логи
tail -50 logs/sentinel_*.log

# Проверить API ключи в .env
grep API .env
```

### Остановить зависший процесс

```bash
# Найти процесс
ps aux | grep main.py

# Убить вручную (если нужно)
kill -9 <PID>

# Или использовать скрипт
./stop.sh
```

---

## Автозапуск при перезагрузке

### Вариант 1: PM2 (рекомендуется для продакшена)

PM2 автоматически настроен при запуске через `ecosystem.config.js`:

```bash
# Запуск через PM2
cd /var/www/Sentinel
pm2 start ecosystem.config.js

# Сохранить конфигурацию для автозапуска
pm2 save

# Настроить автозапуск при перезагрузке (выполняется автоматически)
pm2 startup

# Управление
pm2 status              # Статус
pm2 logs sentinel-bot    # Логи
pm2 restart sentinel-bot # Перезапуск
pm2 stop sentinel-bot    # Остановка
pm2 monit                # Мониторинг в реальном времени
```

### Вариант 2: Systemd

При развертывании через `./deploy.sh` с правами root будет создан systemd service:

```bash
# Включить автозапуск
sudo systemctl enable sentinel-bot

# Запустить
sudo systemctl start sentinel-bot

# Статус
sudo systemctl status sentinel-bot
```

### Вариант 3: Cron

Добавить в crontab:

```bash
crontab -e

# Добавить строку:
@reboot cd /path/to/Sentinel && ./start.sh
```

---

## Безопасность

⚠️ **Важно:**

1. **Никогда не коммитьте `.env` в git!**
2. **Ограничьте права на .env:**
   ```bash
   chmod 600 .env
   ```
3. **Используйте testnet для тестирования:**
   ```bash
   BYBIT_TESTNET=true
   DRY_RUN=true
   ```

---

**Готово!** Теперь вы можете легко управлять ботом одной командой. 🎉

