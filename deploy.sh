#!/bin/bash

###############################################################################
# Sentinel Trading Bot - Automated Deployment Script
# 
# Этот скрипт автоматически разворачивает проект на VPS:
# - Проверяет и устанавливает зависимости
# - Создает виртуальное окружение
# - Устанавливает Python пакеты
# - Настраивает конфигурацию
# - Опционально создает systemd service
###############################################################################

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Переменные
PROJECT_NAME="Sentinel"
PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/venv"
PYTHON_MIN_VERSION="3.9"
LOG_DIR="$PROJECT_DIR/logs"
STORAGE_DIR="$PROJECT_DIR/storage"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
SYSTEMD_SERVICE="/etc/systemd/system/sentinel-bot.service"

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

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Проверка прав root (для systemd)
check_root() {
    if [[ $EUID -eq 0 ]]; then
        ROOT_ACCESS=true
    else
        ROOT_ACCESS=false
    fi
}

# Проверка Python
check_python() {
    print_info "Проверка Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        PYTHON_CMD="python3"
        print_success "Python найден: $(python3 --version)"
        
        # Проверка версии
        REQUIRED_VERSION=$(echo "$PYTHON_MIN_VERSION" | cut -d'.' -f1,2)
        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
            print_error "Требуется Python $PYTHON_MIN_VERSION или выше, найден $PYTHON_VERSION"
            exit 1
        fi
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        PYTHON_CMD="python"
        print_success "Python найден: $(python --version)"
    else
        print_error "Python не найден. Установите Python $PYTHON_MIN_VERSION или выше."
        print_info "Ubuntu/Debian: sudo apt-get update && sudo apt-get install python3 python3-pip python3-venv"
        print_info "CentOS/RHEL: sudo yum install python3 python3-pip"
        exit 1
    fi
}

# Проверка pip
check_pip() {
    print_info "Проверка pip..."
    
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        print_warning "pip не найден. Устанавливаю..."
        
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y python3-pip
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3-pip
            else
                print_error "Не удалось установить pip автоматически. Установите вручную."
                exit 1
            fi
        else
            print_error "Автоматическая установка pip не поддерживается для этой ОС. Установите вручную."
            exit 1
        fi
    fi
    
    print_success "pip найден: $($PYTHON_CMD -m pip --version | head -n1)"
}

# Обновление pip (только в venv, не системно)
upgrade_pip() {
    print_info "Проверка pip..."
    # Не обновляем системный pip, только в venv (будет обновлен после создания venv)
    if [ -d "$VENV_DIR" ]; then
        print_info "Обновление pip в виртуальном окружении..."
        source "$VENV_DIR/bin/activate"
        pip install --upgrade pip --quiet
        print_success "pip обновлен в venv"
    else
        print_info "pip будет обновлен после создания venv"
    fi
}

# Создание виртуального окружения
create_venv() {
    print_info "Проверка виртуального окружения..."
    
    if [ ! -d "$VENV_DIR" ]; then
        print_info "Создание виртуального окружения в $VENV_DIR..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        print_success "Виртуальное окружение создано"
    else
        print_info "Виртуальное окружение уже существует"
    fi
    
    # Активация venv
    source "$VENV_DIR/bin/activate"
    print_success "Виртуальное окружение активировано"
}

# Установка зависимостей
install_dependencies() {
    print_info "Установка зависимостей из $REQUIREMENTS_FILE..."
    
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        print_error "Файл $REQUIREMENTS_FILE не найден!"
        exit 1
    fi
    
    # Обновление pip в venv
    pip install --upgrade pip --quiet
    
    # Установка зависимостей
    pip install -r "$REQUIREMENTS_FILE" --quiet
    
    print_success "Все зависимости установлены"
}

# Создание директорий
create_directories() {
    print_info "Создание необходимых директорий..."
    
    mkdir -p "$LOG_DIR"
    mkdir -p "$STORAGE_DIR"
    
    print_success "Директории созданы"
}

# Настройка .env файла
setup_env() {
    print_info "Настройка конфигурации (.env файл)..."
    
    if [ -f "$ENV_FILE" ]; then
        print_warning "Файл .env уже существует"
        read -p "Перезаписать существующий .env? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Пропускаю настройку .env"
            return
        fi
    fi
    
    # Если есть .env.example, используем его как шаблон
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        print_info "Создан .env на основе .env.example"
        print_warning "⚠️  ВАЖНО: Отредактируйте $ENV_FILE и добавьте ваши API ключи!"
    else
        # Создаем базовый .env файл
        cat > "$ENV_FILE" << EOF
# Exchange Configuration
BYBIT_API_KEY=your_bybit_api_key_here
BYBIT_API_SECRET=your_bybit_api_secret_here
BYBIT_TESTNET=false

# AI Configuration
GROK_API_KEY=your_grok_api_key_here
GROK_MODEL=grok-4-1-fast-reasoning

# Trading Configuration
TRADING_SYMBOL=BTC/USDT
TRADING_TIMEFRAME=30m
TRADING_BALANCE=10.0

# Daily Screener Configuration
SCREENER_ENABLED=true
SCREENER_INTERVAL_HOURS=48
SCREENER_TOP_N=20
SCREENER_MAX_SYMBOLS=1

# Risk Management
STOP_LOSS_PCT=2.0
MIN_RISK_REWARD=1.5
MIN_AI_CONFIDENCE=80.0

# Scheduling
CYCLE_INTERVAL_MINUTES=120

# System Configuration
DRY_RUN=true
LOG_LEVEL=INFO
LOG_ROTATION=100 MB
LOG_RETENTION=30 days
STORAGE_PATH=storage/trades.jsonl
EOF
        print_info "Создан базовый .env файл"
        print_warning "⚠️  ВАЖНО: Отредактируйте $ENV_FILE и добавьте ваши API ключи!"
    fi
    
    # Интерактивная настройка (опционально)
    read -p "Хотите настроить .env интерактивно? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        interactive_env_setup
    fi
}

# Интерактивная настройка .env
interactive_env_setup() {
    print_info "Интерактивная настройка .env..."
    
    read -p "Bybit API Key: " bybit_key
    read -p "Bybit API Secret: " bybit_secret
    read -p "Grok API Key: " grok_key
    read -p "Использовать testnet? (y/N): " -n 1 -r
    echo
    testnet="false"
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        testnet="true"
    fi
    
    read -p "Режим dry-run (тестовый)? (Y/n): " -n 1 -r
    echo
    dry_run="true"
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        dry_run="false"
    fi
    
    # Обновляем .env
    sed -i "s/BYBIT_API_KEY=.*/BYBIT_API_KEY=$bybit_key/" "$ENV_FILE"
    sed -i "s/BYBIT_API_SECRET=.*/BYBIT_API_SECRET=$bybit_secret/" "$ENV_FILE"
    sed -i "s/GROK_API_KEY=.*/GROK_API_KEY=$grok_key/" "$ENV_FILE"
    sed -i "s/BYBIT_TESTNET=.*/BYBIT_TESTNET=$testnet/" "$ENV_FILE"
    sed -i "s/DRY_RUN=.*/DRY_RUN=$dry_run/" "$ENV_FILE"
    
    print_success "Конфигурация обновлена"
}

# Проверка установки
verify_installation() {
    print_info "Проверка установки..."
    
    # Проверка что venv активирован
    if [ -z "$VIRTUAL_ENV" ]; then
        print_error "Виртуальное окружение не активировано!"
        exit 1
    fi
    
    # Проверка основных пакетов
    python3 -c "import ccxt; import pandas; import loguru; import httpx" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "Основные пакеты установлены корректно"
    else
        print_error "Ошибка при проверке пакетов"
        exit 1
    fi
    
    # Проверка структуры проекта
    if [ ! -f "$PROJECT_DIR/main.py" ]; then
        print_error "main.py не найден!"
        exit 1
    fi
    
    print_success "Установка проверена успешно"
}

# Создание systemd service (опционально)
create_systemd_service() {
    if [ "$ROOT_ACCESS" = false ]; then
        print_warning "Для создания systemd service требуются права root"
        print_info "Пропускаю создание systemd service"
        return
    fi
    
    read -p "Создать systemd service для автозапуска? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return
    fi
    
    print_info "Создание systemd service..."
    
    # Определяем пользователя
    SERVICE_USER=$(logname 2>/dev/null || echo "$SUDO_USER" || echo "$USER")
    
    cat > "$SYSTEMD_SERVICE" << EOF
[Unit]
Description=Sentinel Trading Bot
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python $PROJECT_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    print_success "Systemd service создан: $SYSTEMD_SERVICE"
    print_info "Команды для управления:"
    print_info "  sudo systemctl start sentinel-bot    # Запуск"
    print_info "  sudo systemctl stop sentinel-bot     # Остановка"
    print_info "  sudo systemctl enable sentinel-bot     # Автозапуск"
    print_info "  sudo systemctl status sentinel-bot    # Статус"
    print_info "  sudo journalctl -u sentinel-bot -f   # Логи"
}

# Тестовый запуск
test_run() {
    read -p "Выполнить тестовый запуск для проверки? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return
    fi
    
    print_info "Тестовый запуск (5 секунд)..."
    
    timeout 5 python "$PROJECT_DIR/main.py" 2>&1 | head -20 || true
    
    print_success "Тестовый запуск завершен"
}

# Главная функция
main() {
    print_header "🚀 Развертывание $PROJECT_NAME Trading Bot"
    
    check_root
    check_python
    check_pip
    create_venv
    upgrade_pip  # Обновляем pip после создания venv
    install_dependencies
    create_directories
    setup_env
    verify_installation
    create_systemd_service
    
    print_header "✅ Развертывание завершено успешно!"
    
    echo ""
    print_info "Следующие шаги:"
    echo "  1. Отредактируйте $ENV_FILE и добавьте ваши API ключи"
    echo "  2. Активируйте виртуальное окружение: source $VENV_DIR/bin/activate"
    echo "  3. Запустите бота: python $PROJECT_DIR/main.py"
    echo ""
    
    if [ "$ROOT_ACCESS" = true ] && [ -f "$SYSTEMD_SERVICE" ]; then
        echo "  4. Или используйте systemd: sudo systemctl start sentinel-bot"
        echo ""
    fi
    
    test_run
    
    print_success "Готово! Бот готов к работе."
}

# Запуск
main "$@"

