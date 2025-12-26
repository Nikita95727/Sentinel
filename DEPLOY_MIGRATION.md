# 🚀 Команды для миграции на продакшн VPS

## Быстрая миграция (одна команда)

```bash
ssh root@<vps_ip> "cd /var/www/Sentinel && git pull && sudo ./scripts/safe_restart.sh"
```

## Пошаговая миграция

### Шаг 1: Подключиться к VPS
```bash
ssh root@<vps_ip>
```

### Шаг 2: Перейти в директорию проекта
```bash
cd /var/www/Sentinel
```

### Шаг 3: Обновить код
```bash
git pull origin main
# или
git pull origin master
```

### Шаг 4: Выполнить миграцию
```bash
sudo ./scripts/safe_restart.sh
```

Скрипт автоматически:
- ✅ Создаст резервную копию
- ✅ Мигрирует данные
- ✅ Перезапустит бота
- ✅ Проверит что все работает

## Альтернатива: Ручная миграция

Если автоматический скрипт не работает:

```bash
# 1. Активировать venv
source venv/bin/activate

# 2. Запустить миграцию
python3 scripts/migrate_to_modular.py

# 3. Проверить результат
ls -la storage/conservative/trades/
ls -la storage/conservative/analytics/

# 4. Обновить .env (если нужно)
echo "ENABLE_CONSERVATIVE_MODULE=true" >> .env

# 5. Перезапустить бота
pm2 restart ecosystem.config.js

# 6. Проверить статус
pm2 status
pm2 logs sentinel --lines 20
```

## Проверка после миграции

```bash
# Проверить что бот работает
pm2 status

# Проверить что данные мигрированы
ls -la storage/conservative/trades/
ls -la storage/conservative/analytics/

# Проверить логи
pm2 logs sentinel --lines 50

# Проверить что новые файлы создаются
watch -n 5 'ls -lth storage/conservative/trades/ | head -5'
```

## Откат (если что-то пошло не так)

```bash
# 1. Остановить бота
pm2 stop sentinel

# 2. Восстановить из бэкапа
BACKUP_DIR=$(ls -td backup/migration_* | head -1)
cp -r $BACKUP_DIR/storage/* storage/

# 3. Вернуться к старому коду
git checkout <old-commit-hash>

# 4. Перезапустить
pm2 restart ecosystem.config.js
```

