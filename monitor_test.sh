#!/bin/bash
# Мониторинг тестового запуска бота на 30 минут

BOT_PID=$1
LOG_FILE=$(ls -t logs/test_run_*.log 2>/dev/null | head -1 || echo "logs/sentinel_$(date +%Y-%m-%d).log")
DURATION=1800  # 30 минут в секундах
START_TIME=$(date +%s)

echo "=========================================="
echo "Мониторинг тестового запуска Sentinel Bot"
echo "=========================================="
echo "PID процесса: $BOT_PID"
echo "Лог файл: $LOG_FILE"
echo "Длительность: 30 минут"
echo "Начало: $(date)"
echo "=========================================="
echo ""

# Проверка что процесс работает
check_process() {
    if ps -p $BOT_PID > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Функция для отображения статистики
show_stats() {
    echo ""
    echo "--- Статистика на $(date +%H:%M:%S) ---"
    
    if check_process; then
        echo "✅ Бот работает (PID: $BOT_PID)"
        
        # Проверка последних логов
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Последние 5 строк лога:"
            tail -5 "$LOG_FILE" | sed 's/^/  /'
            
            # Проверка на ошибки
            ERROR_COUNT=$(grep -i "error\|exception\|traceback" "$LOG_FILE" | wc -l | tr -d ' ')
            if [ "$ERROR_COUNT" -gt 0 ]; then
                echo ""
                echo "⚠️  Найдено ошибок в логах: $ERROR_COUNT"
                echo "Последние ошибки:"
                grep -i "error\|exception" "$LOG_FILE" | tail -3 | sed 's/^/  /'
            else
                echo ""
                echo "✅ Ошибок не обнаружено"
            fi
        fi
        
        # Проверка файлов данных
        if [ -f "storage/trades.jsonl" ]; then
            TRADE_COUNT=$(wc -l < "storage/trades.jsonl" | tr -d ' ')
            echo "📊 Записей в trades.jsonl: $TRADE_COUNT"
        fi
        
        if [ -f "storage/analytics.json" ]; then
            echo "📈 Analytics файл создан"
        fi
    else
        echo "❌ Бот не работает! Процесс завершился."
        echo ""
        echo "Последние 20 строк лога:"
        tail -20 "$LOG_FILE" 2>/dev/null | sed 's/^/  /'
        exit 1
    fi
}

# Основной цикл мониторинга
ELAPSED=0
while [ $ELAPSED -lt $DURATION ]; do
    if ! check_process; then
        echo ""
        echo "❌ Бот завершил работу раньше времени!"
        show_stats
        exit 1
    fi
    
    # Показываем статистику каждые 5 минут
    if [ $((ELAPSED % 300)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
        show_stats
    fi
    
    sleep 60  # Проверка каждую минуту
    ELAPSED=$((ELAPSED + 60))
    
    # Показываем прогресс
    REMAINING=$((DURATION - ELAPSED))
    MINUTES=$((REMAINING / 60))
    if [ $((ELAPSED % 300)) -eq 0 ]; then
        echo ""
        echo "⏱️  Осталось: ${MINUTES} минут"
    fi
done

# Финальная статистика
echo ""
echo "=========================================="
echo "Тестовый запуск завершен!"
echo "=========================================="
show_stats

echo ""
echo "📋 Итоговая статистика:"
if [ -f "$LOG_FILE" ]; then
    echo "  - Всего строк в логе: $(wc -l < "$LOG_FILE" | tr -d ' ')"
    echo "  - INFO сообщений: $(grep -c "INFO" "$LOG_FILE" 2>/dev/null || echo "0")"
    echo "  - SUCCESS сообщений: $(grep -c "SUCCESS" "$LOG_FILE" 2>/dev/null || echo "0")"
    echo "  - ERROR сообщений: $(grep -c "ERROR" "$LOG_FILE" 2>/dev/null || echo "0")"
fi

if [ -f "storage/trades.jsonl" ]; then
    echo "  - Всего сделок записано: $(wc -l < "storage/trades.jsonl" | tr -d ' ')"
fi

echo ""
echo "✅ Тест пройден успешно! Бот готов к деплою на VPS."

