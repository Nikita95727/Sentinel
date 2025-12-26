# 🚀 Выполнение миграции на продакшн

## Автоматический способ (рекомендуется)

Если у вас настроен SSH доступ:

```bash
# Вариант 1: Если знаете IP/хост VPS
./scripts/execute_migration.sh user@vps_ip /var/www/Sentinel

# Вариант 2: Если используете стандартный путь
./scripts/execute_migration.sh root@your_vps_ip
```

## Ручной способ

### Шаг 1: Подключиться к VPS
```bash
ssh user@vps_ip
cd /var/www/Sentinel
```

### Шаг 2: Обновить код
```bash
git pull origin main  # или ваша ветка
```

### Шаг 3: Убедиться что скрипты на месте
```bash
ls -la scripts/migrate_to_modular.py
ls -la scripts/safe_restart.sh
```

Если скриптов нет, загрузить их:
```bash
# С локальной машины
scp scripts/migrate_to_modular.py user@vps_ip:/var/www/Sentinel/scripts/
scp scripts/safe_restart.sh user@vps_ip:/var/www/Sentinel/scripts/
```

### Шаг 4: Выполнить миграцию
```bash
sudo ./scripts/safe_restart.sh
```

## Что происходит

1. ✅ Создается резервная копия всех данных
2. ✅ Мигрируют файлы в новую структуру
3. ✅ Проверяется целостность данных
4. ✅ Бот перезапускается
5. ✅ Проверяется что все работает

## Проверка после миграции

```bash
# Проверить статус
pm2 status

# Проверить логи
pm2 logs sentinel --lines 20

# Проверить данные
ls -la storage/conservative/trades/
ls -la storage/conservative/analytics/
```

