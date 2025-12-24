#!/bin/bash

###############################################################################
# Sentinel Trading Bot - Status Script
# 
# Проверка статуса бота
# Использование: ./status.sh
###############################################################################

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Переменные
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PID_FILE="$PROJECT_DIR/sentinel.pid"

# Функции для вывода
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка статуса
check_status() {
    echo ""
    print_info "📊 Статус Sentinel Trading Bot"
    echo ""
    
    if [ ! -f "$PID_FILE" ]; then
        print_warning "Бот не запущен (PID файл не найден)"
        echo ""
        print_info "Запуск: ./start.sh"
        exit 0
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ! ps -p "$PID" > /dev/null 2>&1; then
        print_error "Бот не запущен (процесс с PID $PID не найден)"
        print_warning "Удаляю устаревший PID файл"
        rm -f "$PID_FILE"
        echo ""
        print_info "Запуск: ./start.sh"
        exit 1
    fi
    
    # Информация о процессе
    print_success "✅ Бот запущен"
    echo ""
    print_info "PID: $PID"
    
    # Время работы
    if command -v ps &> /dev/null; then
        RUNTIME=$(ps -o etime= -p "$PID" 2>/dev/null | xargs)
        if [ -n "$RUNTIME" ]; then
            print_info "Время работы: $RUNTIME"
        fi
    fi
    
    # Использование ресурсов
    if command -v ps &> /dev/null; then
        CPU_MEM=$(ps -o %cpu,%mem= -p "$PID" 2>/dev/null | xargs)
        if [ -n "$CPU_MEM" ]; then
            CPU=$(echo "$CPU_MEM" | awk '{print $1}')
            MEM=$(echo "$CPU_MEM" | awk '{print $2}')
            print_info "CPU: ${CPU}% | RAM: ${MEM}%"
        fi
    fi
    
    # Последний лог файл
    LATEST_LOG=$(ls -t "$PROJECT_DIR/logs"/*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo ""
        print_info "Последний лог: $LATEST_LOG"
        print_info "Размер: $(du -h "$LATEST_LOG" | cut -f1)"
        
        # Последние строки лога
        echo ""
        print_info "Последние 5 строк лога:"
        echo "---"
        tail -5 "$LATEST_LOG" 2>/dev/null || echo "Не удалось прочитать лог"
        echo "---"
    fi
    
    echo ""
    print_info "Команды:"
    print_info "  ./stop.sh        - Остановить бота"
    print_info "  tail -f $LATEST_LOG  - Смотреть логи в реальном времени"
}

# Главная функция
main() {
    check_status
}

# Запуск
main "$@"

