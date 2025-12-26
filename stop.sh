#!/bin/bash

###############################################################################
# Sentinel Trading Bot - Stop Script
# 
# Остановка бота, запущенного через start.sh
# Использование: ./stop.sh
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

# Остановка бота
stop_bot() {
    if [ ! -f "$PID_FILE" ]; then
        print_warning "PID файл не найден. Бот может быть не запущен."
        print_info "Проверьте процессы: ps aux | grep main.py"
        exit 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ! ps -p "$PID" > /dev/null 2>&1; then
        print_warning "Процесс с PID $PID не найден. Удаляю PID файл."
        rm -f "$PID_FILE"
        exit 1
    fi
    
    print_info "Остановка бота (PID: $PID)..."
    
    # Graceful shutdown
    kill "$PID" 2>/dev/null || true
    
    # Ждем до 10 секунд
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            print_success "Бот остановлен успешно"
            rm -f "$PID_FILE"
            exit 0
        fi
        sleep 1
    done
    
    # Если не остановился, принудительно
    if ps -p "$PID" > /dev/null 2>&1; then
        print_warning "Принудительная остановка..."
        kill -9 "$PID" 2>/dev/null || true
        sleep 1
        
        if ! ps -p "$PID" > /dev/null 2>&1; then
            print_success "Бот остановлен принудительно"
            rm -f "$PID_FILE"
        else
            print_error "Не удалось остановить процесс"
            exit 1
        fi
    fi
}

# Главная функция
main() {
    echo ""
    print_info "🛑 Остановка Sentinel Trading Bot"
    echo ""
    
    stop_bot
    
    echo ""
    print_success "✅ Готово!"
    echo ""
}

# Запуск
main "$@"


