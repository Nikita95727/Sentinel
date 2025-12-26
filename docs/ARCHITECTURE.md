# Sentinel AI Trading Bot - Architecture Documentation

## Overview

Sentinel is an autonomous cryptocurrency trading bot that uses AI (Grok) for decision-making. The architecture is designed for modularity, scalability, and maintainability.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Main Entry Point                       │
│                         (main.py)                            │
└───────────────────────┬───────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│   Exchange   │ │     AI      │ │  Services  │
│  Providers   │ │  Providers   │ │            │
└───────┬──────┘ └──────┬──────┘ └─────┬──────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
              ┌─────────▼─────────┐
              │  Trading Engine    │
              │   (Orchestrator)   │
              └─────────┬───────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│   Storage    │ │  Analytics  │ │   Risk     │
│   Manager    │ │   Service   │ │  Manager   │
└──────────────┘ └─────────────┘ └────────────┘
```

## Core Components

### 1. Trading Engine (`core/engine.py`)

**Purpose**: Main orchestrator that coordinates all components.

**Responsibilities**:
- Execute trading cycles
- Coordinate data fetching, analysis, and execution
- Manage positions
- Handle exit conditions

**Key Methods**:
- `run_cycle()`: Execute one complete trading cycle
- `_run_symbol_cycle()`: Process a single symbol
- `_execute_buy()`: Execute buy order
- `_check_exit_conditions()`: Check if position should be closed

**Dependencies**:
- Exchange Provider
- AI Provider
- Analyzer
- Risk Manager
- State Manager
- Analytics (optional)

### 2. Exchange Providers (`providers/bybit.py`)

**Purpose**: Abstract exchange interactions.

**Responsibilities**:
- Fetch market data (OHLCV, ticker, balance)
- Execute orders
- Handle exchange-specific errors

**Key Features**:
- Circuit breaker protection
- Retry logic with exponential backoff
- Comprehensive error handling

**Error Handling**:
- Network errors → Retry with backoff
- Exchange errors → Log with context
- Insufficient funds → Specific error code

### 3. AI Providers (`providers/grok.py`)

**Purpose**: AI-powered market analysis and decision-making.

**Responsibilities**:
- Analyze market conditions
- Make trading decisions (BUY/SELL/HOLD)
- Select trading symbols
- Learn from trade history

**Key Features**:
- Structured JSON output
- Few-shot examples
- Market phase detection
- Pre/post filters
- Technical fallback

**Error Handling**:
- API timeouts → Technical fallback
- Parse errors → Validation and retry
- Invalid responses → Fallback decision

### 4. Services

#### Analyzer (`services/analyzer.py`)
- Calculate technical indicators (RSI, EMA, ATR)
- Scan top volume coins
- Calculate screening metrics

#### Risk Manager (`services/risk_manager.py`)
- Position sizing (dynamic based on volatility/confidence)
- Stop-loss calculation (ATR-based)
- Take-profit calculation
- Trade validation

#### Analytics (`services/analytics.py`)
- Record AI decisions
- Track performance metrics
- Detect anomalies
- Generate statistics

#### AI Optimizer (`services/ai_optimizer.py`)
- Cache AI responses (30 min TTL)
- Rate limiting (30 min between calls)
- Statistics tracking

### 5. Storage (`storage/state_manager.py`)

**Purpose**: Persist trade history and state.

**Features**:
- Daily JSONL files for trades
- Automatic file rotation
- Old file cleanup
- Trade validation

## Error Handling System

### Error Categories

1. **API_ERROR**: Errors from external APIs (Grok, exchange)
2. **NETWORK_ERROR**: Network connectivity issues
3. **EXCHANGE_ERROR**: Exchange-specific errors
4. **AI_ERROR**: AI-related errors (parsing, validation)
5. **VALIDATION_ERROR**: Input validation failures
6. **DATA_ERROR**: Data loading/saving issues
7. **BUSINESS_LOGIC_ERROR**: Trading logic errors
8. **SYSTEM_ERROR**: System-level errors

### Error Codes

Error codes follow the pattern: `CATEGORY_NUMBER`

Examples:
- `API_1001`: API rate limit
- `EXCH_2002`: Insufficient balance
- `AI_3003`: AI timeout
- `VAL_4001`: Invalid price

### Error Context

Every error includes:
- Error ID (unique identifier)
- Timestamp
- Error code and category
- Severity (low/medium/high/critical)
- Component and operation
- Symbol (if applicable)
- Metadata (additional context)
- Stack trace
- Causal chain (for chained errors)

### Error Logging

Errors are logged with:
1. **Human-readable format**: For console/log files
2. **Structured JSON**: For parsing and analysis
3. **Full context**: Component, operation, metadata
4. **Stack traces**: For debugging

## Data Flow

### Trading Cycle Flow

```
1. Fetch OHLCV data
   ↓
2. Calculate technical indicators
   ↓
3. Technical filter (skip AI if no signal)
   ↓
4. Check AI cache / rate limit
   ↓
5. Call AI (if needed)
   ↓
6. Validate AI decision
   ↓
7. Execute trade (if valid)
   ↓
8. Update state and analytics
```

### Daily Screening Flow

```
1. Scan top-20 coins by volume
   ↓
2. Calculate 7-day ATR for each
   ↓
3. Pre-filter (volume, ATR)
   ↓
4. Determine market phase (BTC 7-day)
   ↓
5. AI selection (with few-shot examples)
   ↓
6. Post-filter (RSI)
   ↓
7. Update active symbols
```

## Configuration

Configuration is managed via `.env` file and `config.py`:

- **Trading**: Balance, stop-loss, risk/reward
- **Screening**: Interval, top N, max symbols
- **AI**: Model, temperature, API key
- **Exchange**: API keys, testnet mode
- **Storage**: Path, retention days

## Logging

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (non-critical)
- **ERROR**: Error messages (recoverable)
- **CRITICAL**: Critical errors (may cause shutdown)

### Log Outputs

1. **Console**: Colored output for development
2. **File**: Rotated daily log files
3. **JSON**: Structured JSON logs for analysis

### Log Format

```
TIMESTAMP | LEVEL | MODULE:FUNCTION:LINE | MESSAGE
```

With context:
```json
{
  "timestamp": "2025-12-24T19:00:00Z",
  "level": "ERROR",
  "error_code": "API_1002",
  "component": "GrokProvider",
  "symbol": "BTC/USDT",
  "operation": "analyze",
  "message": "API timeout",
  "metadata": {...}
}
```

## Resilience Mechanisms

### 1. Circuit Breaker

Protects against cascading failures:
- **Closed**: Normal operation
- **Open**: Blocking requests after threshold
- **Half-open**: Testing recovery

### 2. Retry Logic

Exponential backoff for transient errors:
- Initial delay: 5 seconds
- Backoff multiplier: 2x
- Max attempts: 3

### 3. Fallback Mechanisms

- **AI fallback**: Technical indicators when AI fails
- **Cache**: Reuse recent AI responses
- **Rate limiting**: Prevent API overload

## Security Considerations

1. **API Keys**: Stored in `.env`, never committed
2. **Permissions**: Exchange API keys limited to spot trading
3. **Validation**: All inputs validated before execution
4. **Dry Run**: Test mode prevents real trades

## Performance Optimizations

1. **AI Caching**: 30-minute cache reduces API calls by 75%
2. **Technical Filters**: Skip AI for unpromising signals
3. **Rate Limiting**: Prevent API overload
4. **Async Operations**: Non-blocking I/O

## Extension Points

### Adding New Exchange

1. Create class inheriting `BaseExchange`
2. Implement required methods
3. Add error handling
4. Register in main.py

### Adding New AI Provider

1. Create class inheriting `BaseAI`
2. Implement `analyze()` and `get_system_prompt()`
3. Add error handling
4. Register in main.py

### Adding New Indicators

1. Add calculation in `Analyzer`
2. Include in `calculate_indicators()`
3. Update AI prompt if needed

## Monitoring and Diagnostics

### Error Statistics

Access via `error_handler.get_error_statistics()`:
- Total errors
- Errors by category
- Errors by severity
- Errors by component
- Recent errors

### Analytics

Tracked metrics:
- AI decisions and outcomes
- Trade performance
- Anomaly detection
- Market conditions

### Health Checks

- Exchange connectivity
- AI API availability
- Storage accessibility
- Configuration validity


