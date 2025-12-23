# Architectural Guidelines: Sentinel AI

## 1. Clean Architecture & Patterns
Адаптировать структуру под модульный дизайн, чтобы компоненты были слабо связаны:
- **Dependency Injection:** Все сервисы (Exchange, AI, Storage) передаются в главный движок через конструктор.
- **Provider Pattern:** Биржи и AI-модели реализуются как провайдеры. Добавление новой биржи = новый файл в `providers/`, реализующий интерфейс.

## 2. Стек и Библиотеки
- **Exchange Framework:** `ccxt.pro` (async).
- **AI Integration:** `xai` (Grok API).
- **Scheduling:** `apscheduler` (AsyncIOScheduler).
- **Validation:** `pydantic-settings` (строгая типизация конфига из .env).
- **Logging:** `loguru` (асинхронные логи с ротацией).

## 3. Структура проекта (Обязательно для исполнения)
```text
/sentinel
├── core/
│   ├── base_exchange.py   # Interface для бирж
│   ├── base_ai.py         # Interface для LLM
│   └── engine.py          # Основной цикл управления
├── providers/
│   ├── bybit.py           # Реализация CCXT Bybit
│   └── grok.py            # Реализация Grok API
├── services/
│   ├── analyzer.py        # TA-Lib / Pandas_TA расчеты
│   └── risk_manager.py    # Логика SL/TP и объемов
├── storage/
│   └── state_manager.py   # Работа с JSON/SQLite (Memory)
├── config.py              # Загрузка .env через Pydantic
└── main.py                # Точка входа