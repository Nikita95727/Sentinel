# Sentinel AI Trading Bot

Autonomous cryptocurrency trading bot using AI (Grok) for decision-making.

## ⚠️ IMPORTANT DISCLAIMER

**THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.**

**CURRENT STATUS: MODEL TRAINING PHASE**

This bot is currently in **Phase 0: Data Collection and Model Calibration**. The AI model is being trained and calibrated. Using this bot for real trading carries significant financial risks.

**BY USING THIS SOFTWARE, YOU ACKNOWLEDGE AND AGREE THAT:**

1. **NO WARRANTY**: The author and contributors disclaim all warranties, express or implied, including but not limited to warranties of merchantability, fitness for a particular purpose, and non-infringement.

2. **FINANCIAL RISKS**: Cryptocurrency trading involves substantial risk of loss. You may lose some or all of your invested capital. Past performance does not guarantee future results.

3. **NO LIABILITY**: The author, contributors, and distributors shall not be liable for any direct, indirect, incidental, special, consequential, or exemplary damages, including but not limited to financial losses, trading losses, or any other damages arising from the use or inability to use this software.

4. **USE AT YOUR OWN RISK**: You are solely responsible for any trading decisions and financial outcomes. Always test thoroughly in dry-run mode before using real funds.

5. **NOT FINANCIAL ADVICE**: This software is for educational and research purposes only. It does not constitute financial, investment, or trading advice.

**DO NOT USE THIS BOT FOR REAL TRADING WITHOUT EXTENSIVE TESTING IN DRY-RUN MODE.**

---

## 🚀 Features

### Core Trading Features
- **Dynamic Screening**: Scans top-20 coins by volume every 24-48 hours
- **7-Day Volatility Analysis**: Calculates ATR to assess profit potential
- **AI Asset Selection**: Grok analyzes and selects 1-2 best coins for trading
- **AI-Powered Analysis**: Uses Grok (x.ai) for intelligent market analysis
- **Technical Analysis**: RSI, EMA, ATR indicators via pandas_ta
- **Feedback Learning**: Bot learns from past trades
- **Risk Management**: Automatic position sizing, 2% stop-loss, dynamic take-profit
- **Asynchronous Architecture**: Fully async using ccxt.pro
- **Modular Design**: Easy to add new exchanges or AI providers
- **Daily File Rotation**: Trades stored in daily JSONL files for optimal AI learning

### Dataset Engineering (Teacher-Student Learning)
- **Typed ABSTAIN Decisions**: Three types of abstention for clear dataset structure
  - `TECHNICAL_ABSTAIN`: Technical filters (low volume, negative edge, poor liquidity)
  - `RISK_ABSTAIN`: Risk management (cooldown, trade limits, state conflicts)
  - `AI_ABSTAIN`: AI decision (low confidence, conflicting signals)
- **NO_AI_CALL Events**: Logs when AI is not called due to technical/risk filters
  - Saves API costs
  - Records mathematical rejections before AI evaluation
- **Expected Edge & Total Costs**: Calculated for every decision cycle
  - `expected_edge_percent`: Expected profit percentage
  - `total_costs_percent`: Trading costs (fees + spread + slippage)
  - Automatic TECHNICAL_ABSTAIN if edge <= costs
- **Causal Confidence**: Confidence directly affects execution
  - If confidence < threshold → automatic AI_ABSTAIN
  - Confidence is not decorative, it's causal
- **Action Space Logging**: Records available actions for each decision
  - Shows what was allowed, not just what was chosen
  - Critical for policy learning
- **Separated Reasoning/Decision/Execution**: Clear separation for dataset quality
  - `reasoning`: Why AI thought this way
  - `decision`: What AI chose
  - `execution_result`: What actually happened (EXECUTED, ABSTAINED, HELD, NONE)
- **Exportable for API Flag**: Marks decisions suitable for commercial API
  - Automatic filtering of risky/minimal-edge decisions
  - Prepares data for future API product

## 📋 Requirements

- Python 3.13+
- Bybit account with API keys
- Grok API key (x.ai)
- Minimum $10 on Bybit Spot account

## 🛠 Installation and Setup

### Quick Start (2 commands)

```bash
# 1. Deployment (first time)
./deploy.sh

# 2. Start the bot
./start.sh
```

Done! Bot is running in the background.

📖 **Detailed instructions:** see [QUICK_START.md](QUICK_START.md)

### Bot Management

```bash
./start.sh    # Start bot in background
./stop.sh     # Stop bot
./status.sh   # Check status
```

### Automatic Deployment

The `deploy.sh` script automatically:
- Checks and installs all dependencies
- Creates virtual environment
- Installs Python packages
- Sets up configuration
- Optionally creates systemd service

### Manual Installation

#### 1. Clone and Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

#### 2. Environment Setup

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your data
nano .env
```

Fill in the following required parameters:
- `BYBIT_API_KEY`: Your Bybit API key
- `BYBIT_API_SECRET`: Your Bybit API secret
- `GROK_API_KEY`: Your Grok API key

#### 3. First Run (Test Mode)

```bash
# Make sure DRY_RUN=true in .env
python main.py
```

## 🔧 Configuration

### Module Enable/Disable

Control which modules are active via `.env`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ENABLE_CONSERVATIVE_MODULE` | Enable conservative trading module | `true` |
| `ENABLE_LAUNCH_SNIPER_MODULE` | Enable launch sniper module (high-risk) | `false` |

**Example:**
```bash
# Enable only conservative module
ENABLE_CONSERVATIVE_MODULE=true
ENABLE_LAUNCH_SNIPER_MODULE=false

# Enable both modules
ENABLE_CONSERVATIVE_MODULE=true
ENABLE_LAUNCH_SNIPER_MODULE=true

# Disable all (will exit with error - at least one must be enabled)
ENABLE_CONSERVATIVE_MODULE=false
ENABLE_LAUNCH_SNIPER_MODULE=false
```

### Trading Parameters

Main parameters in `.env`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `DRY_RUN` | Test mode (no real trades) | `true` |
| `TRADING_SYMBOL` | Trading pair | `BTC/USDT` |
| `TRADING_TIMEFRAME` | Candle timeframe | `30m` |
| `TRADING_BALANCE` | Trading balance | `10.0` |
| `STOP_LOSS_PCT` | Stop-loss percentage | `2.0` |
| `CYCLE_INTERVAL_MINUTES` | Cycle interval | `120` |
| `SCREENER_INTERVAL_HOURS` | Screening interval | `48` |
| `SCREENER_MAX_SYMBOLS` | Max symbols to trade | `1` |
| `STORAGE_PATH` | Storage directory | `storage/trades` |
| `STORAGE_RETENTION_DAYS` | File retention period | `30` |

## 📁 Project Structure

```
sentinel/
├── core/
│   ├── base_exchange.py   # Exchange interface
│   ├── base_ai.py         # AI interface
│   └── engine.py          # Main engine
├── providers/
│   ├── bybit.py           # Bybit provider
│   └── grok.py            # Grok AI provider
├── services/
│   ├── analyzer.py        # Technical analysis
│   ├── risk_manager.py    # Risk management
│   ├── analytics.py       # Analytics and metrics
│   ├── report_generator.py # Daily reports
│   └── validator.py       # Safety validation
├── storage/
│   └── state_manager.py   # Trade history management
├── utils/
│   └── export_data.py     # Data export utilities
├── config.py              # Configuration
├── main.py                # Entry point
└── requirements.txt       # Dependencies
```

## 🚀 VPS Deployment

### 1. VPS Preparation (Ubuntu 20.04/22.04)

#### Step 1.1: Connect to VPS

```bash
# Connect to your VPS via SSH
ssh root@your_ip_address
# or
ssh username@your_ip_address
```

#### Step 1.2: Update System

```bash
# Update package lists
sudo apt update

# Upgrade installed packages
sudo apt upgrade -y

# Install basic utilities
sudo apt install -y git curl wget nano build-essential
```

#### Step 1.3: Check Python Version

Check if Python 3.13+ is installed:

```bash
python3 --version
```

**If you already have Python 3.13+ (output `Python 3.13.x`), skip this step and go to Step 1.4.**

**ONLY IF** Python < 3.13 or not installed:

```bash
# 1. Add repository (Ubuntu 20.04 - 24.04)
# Note: On Ubuntu 24.10+ Python 3.13 may be available without PPA
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# 2. Install Python 3.13 and modules
sudo apt install -y python3.13 python3.13-venv python3.13-dev python3-pip

# 3. Update pip
python3.13 -m pip install --upgrade pip

# 4. Verify installation
python3.13 --version
```

### 2. Project Setup

```bash
# Clone project
git clone <your-repo-url> ~/sentinel
cd ~/sentinel

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Create .env from example
cp .env.example .env

# Edit configuration
nano .env
```

⚠️ **IMPORTANT**: Set `DRY_RUN=true` for initial testing!

### 4. Running the Bot

```bash
# Start bot in background
./start.sh

# Check status
./status.sh

# View logs
tail -f logs/sentinel_*.log
```

## 📊 Monitoring

Logs are saved to:
- Console: real-time output
- Files: `logs/sentinel_YYYY-MM-DD.log`
- Trade history: `storage/trades/trades_YYYY-MM-DD.jsonl`
- AI decisions: `storage/analytics/ai_decisions_YYYY-MM-DD.jsonl`
- Market conditions: `storage/analytics/market_conditions_YYYY-MM-DD.jsonl`
- SQLite database: Daily sync for advanced analytics

### Data Format

All decisions are logged in JSONL format with full context:
- `decision_id`: Unique UUID for each decision
- `abstain_type`: Type of ABSTAIN (TECHNICAL_ABSTAIN, RISK_ABSTAIN, AI_ABSTAIN)
- `expected_edge_percent`: Expected profit percentage
- `total_costs_percent`: Trading costs percentage
- `action_space`: Available actions at decision time
- `execution_result`: What actually happened
- `exportable_for_api`: Whether decision is suitable for API export
- `event_type`: Type of event (ai_decision, NO_AI_CALL)

## ⚠️ Important Notes

1. **Testing**: Always start with `DRY_RUN=true` and `BYBIT_TESTNET=true`
2. **API Keys**: Use keys with Spot trading permissions only
3. **Risks**: Cryptocurrency trading involves risks. Only use funds you can afford to lose
4. **Monitoring**: Regularly check logs and trade history
5. **Updates**: Keep track of library updates in requirements.txt
6. **Model Training**: The bot is currently in training phase - use with extreme caution

## 🔐 Security

- Never commit `.env` file to Git
- Use IP whitelist on Bybit for API keys
- Limit API key permissions to Spot trading only
- Regularly rotate API keys
- Use strong passwords and 2FA on exchange accounts

## 📈 Scaling

The bot is designed for easy expansion:
- Adding new exchanges: create a class inheriting `BaseExchange`
- Adding new AI: create a class inheriting `BaseAI`
- Multi-symbol trading: run multiple instances with different `.env` files

## 📚 Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)**: System architecture and component overview
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)**: Common issues and solutions
- **[Error Codes Reference](docs/ERROR_CODES.md)**: Complete error code reference
- **[Grok Nightly Report](docs/grok_nightly_report.md)**: Analysis of Grok's decision-making behavior

## 🎓 Dataset Engineering

This bot is designed as a **research and development system** focused on collecting high-quality data for teacher-student model training.

### Key Principles

1. **Causality**: Every decision has clear cause-effect relationships
2. **Observability**: All decisions are logged with full context
3. **Quality over Quantity**: Better to abstain than to make bad trades
4. **Dataset Purity**: Clean, structured data ready for model training

### Data Structure

Each decision includes:
- Market context (price, volume, session, BTC trend)
- Technical indicators (RSI, EMA, ATR, etc.)
- AI reasoning and confidence
- Expected edge and total costs
- Action space (what was allowed)
- Execution result (what happened)
- Abstain type (if applicable)
- Exportability flag (for API use)

This structure enables:
- Teacher-student learning
- Policy model training
- Causal analysis
- Pattern recognition
- Future API product development

## 🆘 Support

If you encounter issues:
1. Check logs: `tail -f logs/sentinel_*.log`
2. Review [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
3. Check error codes in [Error Codes Reference](docs/ERROR_CODES.md)
4. Check configuration in `.env`
5. Verify API keys are valid
6. Check balance on Bybit
7. Ensure all dependencies are installed

### Error Diagnostics

The bot includes comprehensive error tracking with full context:

```python
from utils.error_handler import error_handler

# Get error statistics
stats = error_handler.get_error_statistics()
print(f"Total errors: {stats['total_errors']}")
print(f"By category: {stats['by_category']}")
print(f"By severity: {stats['by_severity']}")
```

Every error includes:
- Unique error ID
- Error code and category
- Full context (component, operation, symbol)
- Stack trace
- Causal chain (for chained errors)

## 📝 License

MIT License - use at your own risk.

---

## ⚠️ LEGAL DISCLAIMER

**THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.**

**CURRENT STATUS: MODEL TRAINING PHASE**

This trading bot is currently in **Phase 0: Data Collection and Model Calibration**. The AI model is being trained and calibrated using historical and real-time market data. The system is not yet fully optimized for production trading.

**FINANCIAL RISKS:**

- **Cryptocurrency trading involves substantial risk of loss**
- **You may lose some or all of your invested capital**
- **Past performance does not guarantee future results**
- **AI models can make incorrect decisions**
- **Market conditions can change rapidly**

**NO LIABILITY:**

The author, contributors, and distributors of this software:
- **Shall not be liable** for any direct, indirect, incidental, special, consequential, or exemplary damages
- **Shall not be responsible** for any financial losses, trading losses, or other damages
- **Do not guarantee** any trading results or profitability
- **Do not provide** financial, investment, or trading advice

**YOUR RESPONSIBILITY:**

- You are **solely responsible** for all trading decisions
- You must **test extensively** in dry-run mode before using real funds
- You must **understand** the risks involved in cryptocurrency trading
- You must **comply** with all applicable laws and regulations in your jurisdiction
- You must **not use** this software if you cannot afford to lose your investment

**USE AT YOUR OWN RISK. BY USING THIS SOFTWARE, YOU ACKNOWLEDGE THAT YOU HAVE READ, UNDERSTOOD, AND AGREE TO BE BOUND BY THIS DISCLAIMER.**

---

**For questions or issues, please open an issue on GitHub (but remember: no support guarantees).**
