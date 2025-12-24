#!/bin/bash

###############################################################################
# Проверка синхронизации скриптов развертывания с зависимостями
# 
# Этот скрипт проверяет что deploy.sh и другие скрипты актуальны
# относительно requirements.txt и структуры проекта
###############################################################################

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
DEPLOY_SCRIPT="$PROJECT_DIR/deploy.sh"
START_SCRIPT="$PROJECT_DIR/start.sh"
MAIN_SCRIPT="$PROJECT_DIR/main.py"

ERRORS=0
WARNINGS=0

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ERRORS=$((ERRORS + 1))
}

echo ""
echo "🔍 Проверка синхронизации скриптов развертывания"
echo "================================================"
echo ""

# Проверка наличия файлов
print_info "Проверка наличия файлов..."

[ -f "$REQUIREMENTS_FILE" ] && print_success "requirements.txt найден" || print_error "requirements.txt не найден"
[ -f "$DEPLOY_SCRIPT" ] && print_success "deploy.sh найден" || print_error "deploy.sh не найден"
[ -f "$START_SCRIPT" ] && print_success "start.sh найден" || print_error "start.sh не найден"
[ -f "$MAIN_SCRIPT" ] && print_success "main.py найден" || print_error "main.py не найден"

echo ""

# Проверка что deploy.sh использует requirements.txt
print_info "Проверка использования requirements.txt в deploy.sh..."

if grep -q "requirements.txt" "$DEPLOY_SCRIPT"; then
    print_success "deploy.sh использует requirements.txt"
else
    print_error "deploy.sh не использует requirements.txt"
fi

if grep -q "pip install -r.*REQUIREMENTS_FILE\|pip install -r.*requirements.txt" "$DEPLOY_SCRIPT"; then
    print_success "deploy.sh правильно устанавливает зависимости"
else
    print_warning "deploy.sh может не устанавливать зависимости из requirements.txt"
fi

echo ""

# Проверка минимальной версии Python
print_info "Проверка минимальной версии Python..."

PYTHON_MIN_IN_REQUIREMENTS=""
if grep -q "python_requires" "$REQUIREMENTS_FILE" 2>/dev/null; then
    PYTHON_MIN_IN_REQUIREMENTS=$(grep "python_requires" "$REQUIREMENTS_FILE" | head -1)
fi

PYTHON_MIN_IN_DEPLOY=$(grep "PYTHON_MIN_VERSION" "$DEPLOY_SCRIPT" | head -1 | cut -d'"' -f2)

if [ -n "$PYTHON_MIN_IN_DEPLOY" ]; then
    print_success "Минимальная версия Python в deploy.sh: $PYTHON_MIN_IN_DEPLOY"
else
    print_warning "Минимальная версия Python не указана в deploy.sh"
fi

echo ""

# Проверка структуры проекта
print_info "Проверка структуры проекта..."

REQUIRED_DIRS=("core" "providers" "services" "storage" "utils")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$PROJECT_DIR/$dir" ]; then
        print_success "Директория $dir/ существует"
    else
        print_warning "Директория $dir/ не найдена"
    fi
done

echo ""

# Проверка путей в скриптах
print_info "Проверка путей в скриптах..."

if grep -q "main.py" "$START_SCRIPT"; then
    print_success "start.sh правильно ссылается на main.py"
else
    print_error "start.sh не ссылается на main.py"
fi

if grep -q "venv" "$START_SCRIPT"; then
    print_success "start.sh использует venv"
else
    print_error "start.sh не использует venv"
fi

echo ""

# Проверка зависимостей
print_info "Анализ зависимостей в requirements.txt..."

if [ -f "$REQUIREMENTS_FILE" ]; then
    DEP_COUNT=$(grep -v "^#" "$REQUIREMENTS_FILE" | grep -v "^$" | wc -l | xargs)
    print_success "Найдено зависимостей: $DEP_COUNT"
    
    # Проверка критических зависимостей
    CRITICAL_DEPS=("ccxt" "pandas" "loguru" "httpx" "pydantic-settings")
    for dep in "${CRITICAL_DEPS[@]}"; do
        if grep -qi "$dep" "$REQUIREMENTS_FILE"; then
            print_success "Критическая зависимость $dep найдена"
        else
            print_warning "Критическая зависимость $dep не найдена"
        fi
    done
fi

echo ""

# Итоговый отчет
echo "================================================"
echo "📊 Итоговый отчет"
echo "================================================"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    print_success "Все проверки пройдены успешно!"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    print_warning "Найдено предупреждений: $WARNINGS"
    print_info "Рекомендуется проверить предупреждения"
    exit 0
else
    print_error "Найдено ошибок: $ERRORS"
    print_warning "Найдено предупреждений: $WARNINGS"
    print_info "Необходимо исправить ошибки перед развертыванием"
    exit 1
fi

