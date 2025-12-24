#!/bin/bash

###############################################################################
# Sentinel Trading Bot - Start Script
# 
# Простой скрипт для запуска бота в фоне.
# Использование: ./start.sh
###############################################################################

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Переменные
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
VENV_DIR="$PROJECT_DIR/venv"
PID_FILE="$PROJECT_DIR/sentinel.pid"
LOG_FILE="$PROJECT_DIR/logs/bot_$(date +%Y%m%d_%H%M%S).log"
MAIN_SCRIPT="$PROJECT_DIR/main.py"

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

# Проверка что venv существует
check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Виртуальное окружение не найдено в $VENV_DIR"
        print_info "Запустите сначала: ./deploy.sh"
        exit 1
    fi
    
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        print_error "Виртуальное окружение неполное"
        print_info "Запустите сначала: ./deploy.sh"
        exit 1
    fi
}

# Проверка что .env существует
check_env() {
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        print_warning "Файл .env не найден"
        print_info "Создайте .env файл или запустите: ./deploy.sh"
        read -p "Продолжить без .env? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Проверка что main.py существует
check_main() {
    if [ ! -f "$MAIN_SCRIPT" ]; then
        print_error "main.py не найден в $PROJECT_DIR"
        exit 1
    fi
}

# Проверка что бот уже не запущен
check_running() {
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            print_warning "Бот уже запущен (PID: $OLD_PID)"
            print_info "Используйте: ./stop.sh для остановки"
            print_info "Или: ./status.sh для проверки статуса"
            exit 1
        else
            print_info "Удаляю устаревший PID файл"
            rm -f "$PID_FILE"
        fi
    fi
}

# Создание директорий
create_directories() {
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/storage"
}

# Запуск бота
start_bot() {
    print_info "Запуск бота в фоне..."
    
    # Активация venv и запуск
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Запуск в фоне с nohup
    nohup python "$MAIN_SCRIPT" > "$LOG_FILE" 2>&1 &
    BOT_PID=$!
    
    # Сохранение PID
    echo "$BOT_PID" > "$PID_FILE"
    
    # Небольшая задержка для проверки что процесс запустился
    sleep 2
    
    # Проверка что процесс все еще работает
    if ps -p "$BOT_PID" > /dev/null 2>&1; then
        print_success "Бот запущен успешно!"
        echo ""
        print_info "PID: $BOT_PID"
        print_info "Лог файл: $LOG_FILE"
        print_info "PID файл: $PID_FILE"
        echo ""
        print_info "Просмотр логов: tail -f $LOG_FILE"
        print_info "Остановка: ./stop.sh"
        print_info "Статус: ./status.sh"
    else
        print_error "Бот не запустился. Проверьте логи:"
        print_error "  tail -20 $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# Главная функция
main() {
    echo ""
    print_info "🚀 Запуск Sentinel Trading Bot"
    echo ""
    
    check_venv
    check_env
    check_main
    check_running
    create_directories
    start_bot
    
    echo ""
    print_success "✅ Готово! Бот работает в фоне."
    echo ""
}

# Запуск
main "$@"

