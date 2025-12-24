#!/bin/bash

###############################################################################
# Sentinel Bot - Development & Diagnostic Tools
# 
# Служебный скрипт для подключения к VPS и диагностики проблем.
# 
# ⚠️  ВАЖНО: Этот файл в .gitignore и НЕ должен быть закоммичен!
###############################################################################

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# VPS Configuration
VPS_HOST="64.226.114.69"
VPS_USER="root"
VPS_PROJECT_DIR="/root/Sentinel"
SSH_KEY="${HOME}/.ssh/id_rsa"  # Путь к SSH ключу (измените если нужно)

# Функции вывода
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

print_header() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

# Проверка SSH подключения
check_ssh_connection() {
    print_info "Проверка SSH подключения к VPS..."
    
    if ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "echo 'Connection OK'" > /dev/null 2>&1; then
        print_success "SSH подключение работает"
        return 0
    else
        print_error "Не удалось подключиться к VPS"
        print_info "Проверьте:"
        print_info "  1. SSH ключ: $SSH_KEY"
        print_info "  2. Доступность VPS: $VPS_HOST"
        print_info "  3. Правильность пользователя: $VPS_USER"
        return 1
    fi
}

# Выполнение команды на VPS
run_remote() {
    local cmd="$1"
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "$cmd"
}

# Сбор логов
collect_logs() {
    print_header "📋 Сбор логов с VPS"
    
    local log_dir="./vps_logs_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$log_dir"
    
    print_info "Создана директория: $log_dir"
    
    # Последний лог файл
    print_info "Копирование логов..."
    run_remote "find $VPS_PROJECT_DIR/logs -name '*.log' -type f -mtime -1 | head -5" > "$log_dir/log_files.txt" 2>/dev/null || true
    
    # Копирование последних логов
    if run_remote "test -f $VPS_PROJECT_DIR/logs/sentinel_*.log" 2>/dev/null; then
        LATEST_LOG=$(run_remote "ls -t $VPS_PROJECT_DIR/logs/sentinel_*.log 2>/dev/null | head -1")
        if [ -n "$LATEST_LOG" ]; then
            run_remote "tail -500 '$LATEST_LOG'" > "$log_dir/latest_sentinel.log" 2>/dev/null || true
            print_success "Скопирован последний лог: $LATEST_LOG"
        fi
    fi
    
    # Systemd logs если есть
    if run_remote "systemctl is-active sentinel-bot > /dev/null 2>&1" 2>/dev/null; then
        run_remote "journalctl -u sentinel-bot -n 200 --no-pager" > "$log_dir/systemd.log" 2>/dev/null || true
        print_success "Скопированы systemd логи"
    fi
    
    # Bot logs если запущен через start.sh
    if run_remote "test -f $VPS_PROJECT_DIR/sentinel.pid" 2>/dev/null; then
        PID=$(run_remote "cat $VPS_PROJECT_DIR/sentinel.pid 2>/dev/null")
        if [ -n "$PID" ]; then
            run_remote "ps aux | grep $PID" > "$log_dir/process_info.txt" 2>/dev/null || true
        fi
    fi
    
    print_success "Логи собраны в: $log_dir"
}

# Диагностика статуса
diagnose_status() {
    print_header "🔍 Диагностика статуса бота"
    
    # Проверка процесса
    print_info "Проверка процессов..."
    run_remote "ps aux | grep -E 'main.py|sentinel' | grep -v grep" || print_warning "Процесс не найден"
    
    echo ""
    
    # Проверка systemd service
    print_info "Проверка systemd service..."
    if run_remote "systemctl is-active sentinel-bot > /dev/null 2>&1" 2>/dev/null; then
        print_success "Systemd service активен"
        run_remote "systemctl status sentinel-bot --no-pager -l" | head -20
    else
        print_warning "Systemd service не активен"
    fi
    
    echo ""
    
    # Проверка PID файла
    print_info "Проверка PID файла..."
    if run_remote "test -f $VPS_PROJECT_DIR/sentinel.pid" 2>/dev/null; then
        PID=$(run_remote "cat $VPS_PROJECT_DIR/sentinel.pid 2>/dev/null")
        if [ -n "$PID" ]; then
            if run_remote "ps -p $PID > /dev/null 2>&1" 2>/dev/null; then
                print_success "Бот запущен (PID: $PID)"
            else
                print_warning "PID файл существует, но процесс не найден"
            fi
        fi
    else
        print_warning "PID файл не найден"
    fi
    
    echo ""
    
    # Проверка директорий
    print_info "Проверка структуры проекта..."
    run_remote "ls -la $VPS_PROJECT_DIR/ | head -20" || print_error "Проект не найден"
    
    echo ""
    
    # Проверка .env
    print_info "Проверка конфигурации..."
    if run_remote "test -f $VPS_PROJECT_DIR/.env" 2>/dev/null; then
        print_success ".env файл существует"
        # Проверка что ключи заполнены (без показа значений)
        if run_remote "grep -q 'your_.*_here' $VPS_PROJECT_DIR/.env 2>/dev/null"; then
            print_warning ".env содержит placeholder значения"
        else
            print_success ".env настроен"
        fi
    else
        print_error ".env файл не найден"
    fi
    
    echo ""
    
    # Последние логи
    print_info "Последние строки лога:"
    LATEST_LOG=$(run_remote "ls -t $VPS_PROJECT_DIR/logs/*.log 2>/dev/null | head -1")
    if [ -n "$LATEST_LOG" ]; then
        run_remote "tail -20 '$LATEST_LOG'" 2>/dev/null || true
    else
        print_warning "Логи не найдены"
    fi
}

# Сбор данных для диагностики
collect_diagnostics() {
    print_header "📊 Сбор диагностических данных"
    
    local diag_dir="./vps_diagnostics_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$diag_dir"
    
    print_info "Создана директория: $diag_dir"
    
    # Системная информация
    print_info "Сбор системной информации..."
    run_remote "uname -a" > "$diag_dir/system_info.txt" 2>/dev/null || true
    run_remote "df -h" > "$diag_dir/disk_usage.txt" 2>/dev/null || true
    run_remote "free -h" > "$diag_dir/memory.txt" 2>/dev/null || true
    run_remote "uptime" > "$diag_dir/uptime.txt" 2>/dev/null || true
    
    # Python информация
    print_info "Сбор информации о Python..."
    run_remote "python3 --version" > "$diag_dir/python_version.txt" 2>/dev/null || true
    run_remote "which python3" >> "$diag_dir/python_version.txt" 2>/dev/null || true
    
    # Проект информация
    print_info "Сбор информации о проекте..."
    run_remote "cd $VPS_PROJECT_DIR && pwd" > "$diag_dir/project_path.txt" 2>/dev/null || true
    run_remote "cd $VPS_PROJECT_DIR && ls -la" > "$diag_dir/project_files.txt" 2>/dev/null || true
    run_remote "cd $VPS_PROJECT_DIR && test -d venv && echo 'venv exists' || echo 'venv missing'" > "$diag_dir/venv_status.txt" 2>/dev/null || true
    
    # Процессы
    print_info "Сбор информации о процессах..."
    run_remote "ps aux | grep -E 'python|sentinel|main.py'" > "$diag_dir/processes.txt" 2>/dev/null || true
    
    # Логи ошибок
    print_info "Поиск ошибок в логах..."
    run_remote "grep -i 'error\|exception\|traceback' $VPS_PROJECT_DIR/logs/*.log 2>/dev/null | tail -50" > "$diag_dir/errors.log" 2>/dev/null || true
    
    # Конфигурация (без секретов)
    print_info "Сбор конфигурации (без секретов)..."
    run_remote "cd $VPS_PROJECT_DIR && grep -v 'API_KEY\|API_SECRET\|SECRET' .env 2>/dev/null" > "$diag_dir/config_safe.txt" 2>/dev/null || true
    
    print_success "Диагностические данные собраны в: $diag_dir"
    print_info "Проверьте файлы в директории для анализа проблем"
}

# Авторазвертывание
auto_deploy() {
    print_header "🚀 Автоматическое развертывание на VPS"
    
    print_warning "Это перезапишет текущую установку на VPS!"
    read -p "Продолжить? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Отменено"
        return
    fi
    
    # Проверка что проект существует локально
    if [ ! -f "./deploy.sh" ]; then
        print_error "deploy.sh не найден в текущей директории"
        return 1
    fi
    
    print_info "Копирование проекта на VPS..."
    
    # Создание директории на VPS
    run_remote "mkdir -p $VPS_PROJECT_DIR"
    
    # Копирование файлов (исключая venv, logs, .env)
    print_info "Синхронизация файлов..."
    rsync -avz --progress \
        -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
        --exclude 'venv/' \
        --exclude 'logs/' \
        --exclude '.env' \
        --exclude '__pycache__/' \
        --exclude '*.pyc' \
        --exclude '.git/' \
        --exclude 'vps_*' \
        --exclude '.dev-tools.sh' \
        ./ "$VPS_USER@$VPS_HOST:$VPS_PROJECT_DIR/"
    
    print_success "Файлы скопированы"
    
    # Запуск deploy.sh на VPS
    print_info "Запуск deploy.sh на VPS..."
    run_remote "cd $VPS_PROJECT_DIR && chmod +x deploy.sh && ./deploy.sh" || {
        print_error "Ошибка при развертывании"
        return 1
    }
    
    print_success "Развертывание завершено"
}

# Быстрая диагностика
quick_diagnose() {
    print_header "⚡ Быстрая диагностика"
    
    # Статус процесса
    if run_remote "ps aux | grep -E 'main.py' | grep -v grep" > /dev/null 2>&1; then
        print_success "✅ Бот запущен"
    else
        print_error "❌ Бот не запущен"
    fi
    
    # Последняя ошибка
    LATEST_LOG=$(run_remote "ls -t $VPS_PROJECT_DIR/logs/*.log 2>/dev/null | head -1")
    if [ -n "$LATEST_LOG" ]; then
        ERROR=$(run_remote "tail -100 '$LATEST_LOG' | grep -i 'error\|exception' | tail -1" 2>/dev/null || true)
        if [ -n "$ERROR" ]; then
            print_warning "Последняя ошибка:"
            echo "$ERROR"
        else
            print_success "Ошибок в последних 100 строках не найдено"
        fi
    fi
    
    # Последняя активность
    if [ -n "$LATEST_LOG" ]; then
        LAST_ACTIVITY=$(run_remote "tail -1 '$LATEST_LOG' | awk '{print \$1, \$2}'" 2>/dev/null || true)
        if [ -n "$LAST_ACTIVITY" ]; then
            print_info "Последняя активность: $LAST_ACTIVITY"
        fi
    fi
}

# Просмотр логов в реальном времени
tail_logs() {
    print_header "📺 Просмотр логов в реальном времени"
    
    LATEST_LOG=$(run_remote "ls -t $VPS_PROJECT_DIR/logs/*.log 2>/dev/null | head -1")
    if [ -n "$LATEST_LOG" ]; then
        print_info "Просмотр: $LATEST_LOG"
        print_info "Нажмите Ctrl+C для выхода"
        echo ""
        run_remote "tail -f '$LATEST_LOG'"
    else
        print_error "Логи не найдены"
    fi
}

# Перезапуск бота
restart_bot() {
    print_header "🔄 Перезапуск бота"
    
    # Остановка
    print_info "Остановка бота..."
    if run_remote "test -f $VPS_PROJECT_DIR/stop.sh" 2>/dev/null; then
        run_remote "cd $VPS_PROJECT_DIR && ./stop.sh" || true
    elif run_remote "systemctl is-active sentinel-bot > /dev/null 2>&1" 2>/dev/null; then
        run_remote "systemctl stop sentinel-bot" || true
    else
        # Убить процесс вручную
        PID=$(run_remote "ps aux | grep 'main.py' | grep -v grep | awk '{print \$2}' | head -1" 2>/dev/null || true)
        if [ -n "$PID" ]; then
            run_remote "kill $PID" || true
        fi
    fi
    
    sleep 2
    
    # Запуск
    print_info "Запуск бота..."
    if run_remote "test -f $VPS_PROJECT_DIR/start.sh" 2>/dev/null; then
        run_remote "cd $VPS_PROJECT_DIR && ./start.sh"
    elif run_remote "systemctl start sentinel-bot" 2>/dev/null; then
        run_remote "systemctl start sentinel-bot"
    else
        print_error "Не удалось запустить бота"
        return 1
    fi
    
    print_success "Бот перезапущен"
}

# Меню
show_menu() {
    echo ""
    print_header "🛠️  Инструменты разработчика Sentinel Bot"
    echo ""
    echo "  1) 🔍 Быстрая диагностика"
    echo "  2) 📋 Собрать логи"
    echo "  3) 📊 Собрать диагностические данные"
    echo "  4) 🔍 Полная диагностика статуса"
    echo "  5) 📺 Просмотр логов в реальном времени"
    echo "  6) 🔄 Перезапустить бота"
    echo "  7) 🚀 Авторазвертывание на VPS"
    echo "  8) 🔌 SSH подключение (интерактивно)"
    echo "  0) Выход"
    echo ""
}

# Главная функция
main() {
    # Проверка SSH подключения
    if ! check_ssh_connection; then
        print_error "Не удалось подключиться к VPS. Проверьте настройки."
        exit 1
    fi
    
    while true; do
        show_menu
        read -p "Выберите действие: " choice
        
        case $choice in
            1)
                quick_diagnose
                ;;
            2)
                collect_logs
                ;;
            3)
                collect_diagnostics
                ;;
            4)
                diagnose_status
                ;;
            5)
                tail_logs
                ;;
            6)
                restart_bot
                ;;
            7)
                auto_deploy
                ;;
            8)
                print_info "Подключение к VPS..."
                ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST"
                ;;
            0)
                print_info "Выход"
                exit 0
                ;;
            *)
                print_error "Неверный выбор"
                ;;
        esac
        
        echo ""
        read -p "Нажмите Enter для продолжения..."
    done
}

# Запуск
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi

