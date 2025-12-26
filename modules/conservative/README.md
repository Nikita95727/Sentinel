# Conservative Trading Module

**Консервативная AI-торговая стратегия для Sentinel бота.**

---

## 📋 Описание

Этот модуль реализует консервативную торговую стратегию с:
- Daily screening (выбор символов каждые 48 часов)
- AI-powered analysis (Grok)
- Technical filters
- Risk management
- Причинно-следственным логированием
- JSONL датасетами

---

## 🏗️ Структура модуля

```
modules/conservative/
├── module.py          # TradingModule interface implementation
├── scheduler.py       # Module-specific scheduler
├── screening.py       # Daily screening logic
├── config.py          # Module configuration
├── execution/
│   └── engine.py      # Trading engine (moved from core/engine.py)
└── README.md
```

---

## 📊 Хранение данных

Модуль использует изолированные пути:
- **Trades:** `storage/conservative/trades/trades_*.jsonl`
- **Analytics:** `storage/conservative/analytics/ai_decisions_*.jsonl`
- **Market Conditions:** `storage/conservative/analytics/market_conditions_*.jsonl`

**Не пересекается с другими модулями.**

---

## ⚙️ Конфигурация

Настройки в `modules/conservative/config.py`:
- `TRADING_SYMBOL`: Символ по умолчанию
- `CYCLE_INTERVAL_MINUTES`: Интервал торгового цикла
- `SCREENER_INTERVAL_HOURS`: Интервал скрининга
- `TRADING_BALANCE`: Баланс для торговли
- `STOP_LOSS_PCT`: Процент стоп-лосса

---

## 🚀 Использование

Модуль запускается через главный entry point:

```python
from modules.conservative.module import ConservativeModule
from core.app import SentinelApp

app = SentinelApp(config)
await app.initialize()

module = ConservativeModule(app.core_context)
app.register_module(module)

await app.start_all()
```

---

## 🔒 Изоляция

Модуль полностью изолирован:
- ✅ Собственные пути хранения данных
- ✅ Собственный scheduler
- ✅ Не влияет на другие модули
- ✅ Не использует общий баланс/риск-менеджмент

---

**Версия:** 1.0.0  
**Статус:** Production

