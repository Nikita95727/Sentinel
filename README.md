# Sentinel AI Trading Bot

Автономный торговый бот для криптовалют с использованием AI (Grok) для принятия решений.

## 🚀 Особенности

- **Динамический скрининг**: Каждые 24 часа сканирует топ-20 монет по объему
- **7-дневная волатильность**: Рассчитывает ATR для оценки потенциала прибыли
- **AI выбор активов**: Grok анализирует и выбирает 1-2 лучших монеты для торговли
- **AI-powered анализ**: Использует Grok (x.ai) для интеллектуального анализа рынка
- **Технический анализ**: RSI, EMA, ATR индикаторы через pandas_ta
- **Обучение с обратной связью**: Бот учится на своих прошлых сделках
- **Риск-менеджмент**: Автоматический расчет позиции, стоп-лосс 2%, динамический тейк-профит
- **Асинхронная архитектура**: Полностью async с использованием ccxt.pro
- **Модульный дизайн**: Легко добавить новые биржи или AI-провайдеры

## 📋 Требования

- Python 3.13+
- Аккаунт Bybit с API ключами
- API ключ Grok (x.ai)
- Минимум $10 на Bybit Spot счету

## 🛠 Установка

### 1. Клонирование и установка зависимостей

```bash
# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
# Скопировать пример конфигурации
cp .env.example .env

# Отредактировать .env своими данными
nano .env
```

Заполните следующие обязательные параметры:
- `BYBIT_API_KEY`: Ваш Bybit API ключ
- `BYBIT_API_SECRET`: Ваш Bybit API секрет
- `GROK_API_KEY`: Ваш Grok API ключ

### 3. Первый запуск (тестовый режим)

```bash
# Убедитесь, что DRY_RUN=true в .env
python main.py
```

## 🔧 Конфигурация

Основные параметры в `.env`:

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `DRY_RUN` | Тестовый режим (без реальных сделок) | `true` |
| `TRADING_SYMBOL` | Торговая пара | `BTC/USDT` |
| `TRADING_TIMEFRAME` | Таймфрейм свечей | `30m` |
| `TRADING_BALANCE` | Баланс для торговли | `10.0` |
| `STOP_LOSS_PCT` | Процент стоп-лосса | `2.0` |
| `CYCLE_INTERVAL_MINUTES` | Интервал циклов | `30` |

## 📁 Структура проекта

```
sentinel/
├── core/
│   ├── base_exchange.py   # Interface для бирж
│   ├── base_ai.py         # Interface для AI
│   └── engine.py          # Основной движок
├── providers/
│   ├── bybit.py           # Bybit провайдер
│   └── grok.py            # Grok AI провайдер
├── services/
│   ├── analyzer.py        # Технический анализ
│   └── risk_manager.py    # Риск-менеджмент
├── storage/
│   └── state_manager.py   # Управление историей
├── config.py              # Конфигурация
├── main.py                # Точка входа
└── requirements.txt       # Зависимости
```

## 🚀 Деплой на VPS (PM2)

### 1. Подготовка VPS (Ubuntu 20.04/22.04)

#### Шаг 1.1: Подключение к VPS

```bash
# Подключитесь к вашему VPS через SSH
ssh root@ваш_ip_адрес
# или
ssh username@ваш_ip_адрес
```

#### Шаг 1.2: Обновление системы

```bash
# Обновить списки пакетов
sudo apt update

# Обновить установленные пакеты
sudo apt upgrade -y

# Установить базовые утилиты
sudo apt install -y git curl wget nano build-essential
```

#### Шаг 1.3: Проверка версии Python

Проверьте, установлен ли Python 3.13+:

```bash
python3 --version
```

**Если у вас уже установлен Python 3.13+ (вывод `Python 3.13.x`), пропустите этот шаг и переходите сразу к Шагу 1.4.**

**ТОЛЬКО ЕСЛИ** Python < 3.13 или не установлен:

```bash
# 1. Добавить репозиторий (только для Ubuntu 20.04 - 24.04)
# Примечание: На Ubuntu 24.10+ Python 3.13 может быть доступен без PPA
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# 2. Установить Python 3.13 и модули
sudo apt install -y python3.13 python3.13-venv python3.13-dev python3-pip

# 3. Обновить pip
python3.13 -m pip install --upgrade pip

# 4. Проверить установку
python3.13 --version
```

#### Шаг 1.4: Установка Node.js и PM2

```bash
# Установить Node.js (LTS версия)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# Проверить установку Node.js и npm
node --version
npm --version

# Установить PM2 глобально
sudo npm install -g pm2

# Проверить установку PM2
pm2 --version
```

### 2. Загрузка проекта

```bash
# Клонировать проект
git clone <your-repo-url> ~/sentinel
cd ~/sentinel

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### 3. Настройка

```bash
# Создать .env из примера
cp .env.example .env

# Отредактировать конфигурацию
nano .env
```

⚠️ **ВАЖНО**: Установите `DRY_RUN=true` для первоначального тестирования!

### 4. Запуск через PM2

```bash
# Создать PM2 конфигурацию
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'sentinel-bot',
    script: 'venv/bin/python',
    args: 'main.py',
    cwd: '~/sentinel',
    interpreter: 'none',
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      PYTHONUNBUFFERED: '1'
    }
  }]
}
EOF

# Запустить бота
pm2 start ecosystem.config.js

# Сохранить конфигурацию PM2
pm2 save

# Автозапуск при перезагрузке
pm2 startup
```

### 5. Управление ботом

```bash
# Просмотр логов
pm2 logs sentinel-bot

# Остановить бота
pm2 stop sentinel-bot

# Перезапустить бота
pm2 restart sentinel-bot

# Статус
pm2 status

# Мониторинг
pm2 monit
```

## 📊 Мониторинг

Логи сохраняются в:
- Консоль: `pm2 logs sentinel-bot`
- Файлы: `logs/sentinel_YYYY-MM-DD.log`
- История сделок: `storage/history.json`

## ⚠️ Важные замечания

1. **Тестирование**: Всегда начинайте с `DRY_RUN=true` и `BYBIT_TESTNET=true`
2. **API ключи**: Используйте ключи только с правами на Spot торговлю
3. **Риски**: Торговля криптовалютами сопряжена с рисками. Используйте только те средства, потерю которых вы можете себе позволить
4. **Мониторинг**: Регулярно проверяйте логи и историю сделок
5. **Обновления**: Следите за обновлениями библиотек в requirements.txt

## 🔐 Безопасность

- Никогда не коммитьте файл `.env` в Git
- Используйте IP whitelist на Bybit для API ключей
- Ограничьте разрешения API ключей только Spot торговлей
- Регулярно меняйте API ключи

## 📈 Масштабирование

Бот спроектирован для легкого расширения:
- Добавление новых бирж: создайте класс, наследующий `BaseExchange`
- Добавление новых AI: создайте класс, наследующий `BaseAI`
- Мульти-символьная торговля: запустите несколько экземпляров с разными `.env`

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи: `pm2 logs sentinel-bot`
2. Проверьте конфигурацию в `.env`
3. Убедитесь, что API ключи валидны
4. Проверьте баланс на Bybit

## 📝 Лицензия

MIT License - используйте на свой риск.

---

**Disclaimer**: Данный бот предоставляется "как есть". Автор не несет ответственности за финансовые потери. Торгуйте на свой страх и риск.
