# Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Sentinel trading bot.

## Error Code Reference

### API Errors (API_1xxx)

#### API_1001: Rate Limit
**Symptoms**: API requests being throttled
**Causes**: Too many requests to Grok API
**Solutions**:
- Check AI Optimizer cache hit rate
- Increase `cache_ttl_minutes` in AI Optimizer
- Reduce `cycle_interval_minutes` in config
- Check Grok API rate limits

**Example Log**:
```
[API_1001] API_ERROR in GrokProvider during analyze for BTC/USDT: Rate limit exceeded
```

#### API_1002: Timeout
**Symptoms**: AI analysis taking too long
**Causes**: Network issues, API overload
**Solutions**:
- Check network connectivity
- Increase timeout in GrokProvider
- Technical fallback will be used automatically

**Example Log**:
```
[API_1002] AI_ERROR in GrokProvider during analyze for BTC/USDT: Request timeout
```

#### API_1005: Server Error
**Symptoms**: 5xx HTTP errors from API
**Causes**: API server issues
**Solutions**:
- Wait and retry (automatic)
- Check Grok API status
- Technical fallback will be used

### Exchange Errors (EXCH_2xxx)

#### EXCH_2001: Connection Failed
**Symptoms**: Cannot connect to exchange
**Causes**: Network issues, exchange downtime
**Solutions**:
- Check internet connection
- Verify exchange is operational
- Check firewall settings
- Retry logic will attempt recovery

**Example Log**:
```
[EXCH_2001] NETWORK_ERROR in BybitProvider during fetch_ohlcv for BTC/USDT: Connection timeout
```

#### EXCH_2002: Insufficient Balance
**Symptoms**: Order rejected due to insufficient funds
**Causes**: Not enough balance for trade
**Solutions**:
- Check account balance
- Reduce position size
- Verify balance calculation

**Example Log**:
```
[EXCH_2002] EXCHANGE_ERROR in BybitProvider during create_market_order for BTC/USDT: Insufficient balance
```

#### EXCH_2003: Invalid Symbol
**Symptoms**: Symbol not found or invalid
**Causes**: Symbol format incorrect, symbol delisted
**Solutions**:
- Verify symbol format (e.g., "BTC/USDT")
- Check if symbol is still traded
- Update symbol list

#### EXCH_2004: Order Rejected
**Symptoms**: Order rejected by exchange
**Causes**: Invalid order parameters, market closed
**Solutions**:
- Check order parameters
- Verify market is open
- Check exchange-specific requirements

#### EXCH_2005: Market Data Error
**Symptoms**: Cannot fetch market data
**Causes**: Exchange API issues, invalid parameters
**Solutions**:
- Verify symbol is valid
- Check exchange API status
- Retry logic will attempt recovery

### AI Errors (AI_3xxx)

#### AI_3001: Parse Error
**Symptoms**: Cannot parse AI response
**Causes**: AI returned invalid JSON
**Solutions**:
- Check AI response format
- Verify system prompt
- Fallback decision will be used

**Example Log**:
```
[AI_3001] AI_ERROR in GrokProvider during analyze for BTC/USDT: Invalid JSON response
```

#### AI_3002: Validation Failed
**Symptoms**: AI decision failed logical validation
**Causes**: AI made illogical decision (e.g., BUY with RSI > 80)
**Solutions**:
- Review validation rules
- Check market conditions
- Fallback decision will be used

#### AI_3003: Timeout
**Symptoms**: AI analysis timeout
**Causes**: API slow response
**Solutions**:
- Increase timeout
- Check network
- Technical fallback will be used

#### AI_3004: Invalid Decision
**Symptoms**: AI returned invalid action
**Causes**: AI response doesn't match expected format
**Solutions**:
- Check system prompt
- Verify response parsing
- Fallback decision will be used

#### AI_3005: Fallback Used
**Symptoms**: Technical fallback activated
**Causes**: AI unavailable or failed
**Solutions**:
- Check AI API status
- Review error logs
- Fallback uses technical indicators only

### Validation Errors (VAL_4xxx)

#### VAL_4001: Invalid Price
**Symptoms**: Price validation failed
**Causes**: Price <= 0 or invalid
**Solutions**:
- Check market data
- Verify price source
- Review validation logic

#### VAL_4002: Invalid Size
**Symptoms**: Position size validation failed
**Causes**: Size <= 0 or exceeds balance
**Solutions**:
- Check balance
- Review position sizing logic
- Verify risk parameters

#### VAL_4003: Blacklisted Symbol
**Symptoms**: Symbol in blacklist
**Causes**: Symbol is in risk manager blacklist
**Solutions**:
- Remove from blacklist if needed
- Use different symbol
- Review blacklist criteria

#### VAL_4004: Insufficient Funds
**Symptoms**: Not enough funds for trade
**Causes**: Trade value exceeds balance
**Solutions**:
- Check account balance
- Reduce position size
- Review risk parameters

### Data Errors (DATA_5xxx)

#### DATA_5001: Load Failed
**Symptoms**: Cannot load data file
**Causes**: File missing, permissions, corruption
**Solutions**:
- Check file exists
- Verify permissions
- Check disk space

#### DATA_5002: Save Failed
**Symptoms**: Cannot save data
**Causes**: Disk full, permissions, I/O error
**Solutions**:
- Check disk space
- Verify permissions
- Check I/O errors

#### DATA_5003: Data Corrupted
**Symptoms**: Data file corrupted
**Causes**: File corruption, incomplete write
**Solutions**:
- Restore from backup
- Recreate file
- Check disk health

#### DATA_5004: Insufficient Data
**Symptoms**: Not enough data for analysis
**Causes**: New symbol, insufficient candles
**Solutions**:
- Wait for more data
- Use different timeframe
- Check data source

### Business Logic Errors (BL_6xxx)

#### BL_6001: Business Logic Error
**Symptoms**: Trading logic error
**Causes**: Unexpected condition in trading cycle
**Solutions**:
- Review error context
- Check trading logic
- Verify state consistency

## Common Issues

### Bot Not Starting

**Symptoms**: Bot fails to start
**Diagnosis**:
1. Check configuration errors in logs
2. Verify API keys in `.env`
3. Check Python version (3.13+)
4. Verify dependencies installed

**Solutions**:
```bash
# Check logs
tail -f logs/sentinel_*.log

# Verify configuration
python -c "from config import settings; print(settings)"

# Check API keys
grep -E "API_KEY|API_SECRET" .env
```

### No Trades Executed

**Symptoms**: Bot running but no trades
**Diagnosis**:
1. Check if dry-run mode is enabled
2. Verify AI confidence threshold (>= 80%)
3. Check technical filter logs
4. Review AI decisions

**Solutions**:
```bash
# Check dry-run status
grep DRY_RUN .env

# Check AI decisions
grep "AI Decision" logs/sentinel_*.log

# Check technical filter
grep "Technical filter" logs/sentinel_*.log
```

### High API Costs

**Symptoms**: API costs higher than expected
**Diagnosis**:
1. Check AI Optimizer statistics
2. Review cache hit rate
3. Verify rate limiting
4. Check cycle interval

**Solutions**:
```python
# Check optimizer stats
from services.ai_optimizer import AIOptimizer
optimizer.get_statistics()
```

### Circuit Breaker Open

**Symptoms**: Requests blocked by circuit breaker
**Diagnosis**:
1. Check error logs for repeated failures
2. Verify service availability
3. Review circuit breaker state

**Solutions**:
```python
# Reset circuit breaker
from utils.resilience import exchange_circuit, ai_circuit
exchange_circuit.reset()
ai_circuit.reset()
```

### Insufficient Data Errors

**Symptoms**: "Insufficient market data" errors
**Diagnosis**:
1. Check exchange connectivity
2. Verify symbol is valid
3. Check timeframe availability

**Solutions**:
- Verify exchange is operational
- Check symbol format
- Try different timeframe

## Diagnostic Commands

### Check Error Statistics

```python
from utils.error_handler import error_handler
stats = error_handler.get_error_statistics()
print(stats)
```

### View Recent Errors

```bash
# From logs
grep "ERROR_CONTEXT" logs/sentinel_*.log | tail -20

# From JSON logs
tail -20 logs/sentinel_*.jsonl | jq '.'
```

### Check Component Health

```python
# Check exchange
from providers.bybit import BybitProvider
exchange = BybitProvider(...)
await exchange.initialize()
balance = await exchange.get_balance()

# Check AI
from providers.grok import GrokProvider
ai = GrokProvider(...)
# Test with simple analysis
```

### Monitor Real-time

```bash
# Watch logs
tail -f logs/sentinel_$(date +%Y-%m-%d).log

# Watch errors only
tail -f logs/sentinel_*.log | grep -i error

# Watch AI decisions
tail -f logs/sentinel_*.log | grep "AI Decision"
```

## Error Context Analysis

Every error includes full context for diagnosis:

```json
{
  "error_id": "a1b2c3d4",
  "timestamp": "2025-12-24T19:00:00Z",
  "error_code": "API_1002",
  "category": "api_error",
  "severity": "high",
  "message": "Request timeout",
  "component": "GrokProvider",
  "symbol": "BTC/USDT",
  "operation": "analyze",
  "metadata": {
    "timeout": 30.0,
    "retry_count": 2
  },
  "stack_trace": "...",
  "causal_chain": []
}
```

Use this context to:
1. Identify the component and operation
2. Understand the error conditions
3. Trace the causal chain
4. Determine appropriate fix

## Getting Help

If issues persist:

1. **Collect Diagnostics**:
   - Error statistics
   - Recent error logs
   - Configuration
   - System info

2. **Check Documentation**:
   - Architecture docs
   - Configuration guide
   - API documentation

3. **Review Logs**:
   - Full error context
   - Stack traces
   - Causal chains

4. **Verify Environment**:
   - Python version
   - Dependencies
   - API keys
   - Network connectivity

