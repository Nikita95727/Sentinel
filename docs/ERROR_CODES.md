# Error Codes Reference

Complete reference of all error codes used in the Sentinel trading bot.

## Error Code Format

Error codes follow the pattern: `CATEGORY_NUMBER`

- **Category**: 2-4 letter prefix (API, EXCH, AI, VAL, DATA, BL, SYS)
- **Number**: 4-digit number (1001-7999)

## API Errors (API_1xxx)

| Code | Name | Severity | Description |
|------|------|----------|-------------|
| API_1001 | Rate Limit | HIGH | API rate limit exceeded |
| API_1002 | Timeout | HIGH | API request timeout |
| API_1003 | Auth Failed | CRITICAL | API authentication failed |
| API_1004 | Invalid Response | MEDIUM | API returned invalid response |
| API_1005 | Server Error | HIGH | API server error (5xx) |

## Exchange Errors (EXCH_2xxx)

| Code | Name | Severity | Description |
|------|------|----------|-------------|
| EXCH_2001 | Connection Failed | HIGH | Cannot connect to exchange |
| EXCH_2002 | Insufficient Balance | HIGH | Not enough balance for trade |
| EXCH_2003 | Invalid Symbol | MEDIUM | Symbol not found or invalid |
| EXCH_2004 | Order Rejected | HIGH | Order rejected by exchange |
| EXCH_2005 | Market Data Error | MEDIUM | Cannot fetch market data |

## AI Errors (AI_3xxx)

| Code | Name | Severity | Description |
|------|------|----------|-------------|
| AI_3001 | Parse Error | MEDIUM | Cannot parse AI response |
| AI_3002 | Validation Failed | MEDIUM | AI decision failed validation |
| AI_3003 | Timeout | HIGH | AI analysis timeout |
| AI_3004 | Invalid Decision | MEDIUM | AI returned invalid decision |
| AI_3005 | Fallback Used | LOW | Technical fallback activated |

## Validation Errors (VAL_4xxx)

| Code | Name | Severity | Description |
|------|------|----------|-------------|
| VAL_4001 | Invalid Price | MEDIUM | Price validation failed |
| VAL_4002 | Invalid Size | MEDIUM | Position size validation failed |
| VAL_4003 | Blacklisted Symbol | LOW | Symbol in blacklist |
| VAL_4004 | Insufficient Funds | HIGH | Not enough funds for trade |

## Data Errors (DATA_5xxx)

| Code | Name | Severity | Description |
|------|------|----------|-------------|
| DATA_5001 | Load Failed | HIGH | Cannot load data file |
| DATA_5002 | Save Failed | HIGH | Cannot save data |
| DATA_5003 | Data Corrupted | CRITICAL | Data file corrupted |
| DATA_5004 | Insufficient Data | MEDIUM | Not enough data for analysis |

## Business Logic Errors (BL_6xxx)

| Code | Name | Severity | Description |
|------|------|----------|-------------|
| BL_6001 | Business Logic Error | HIGH | Trading logic error |

## System Errors (SYS_7xxx)

| Code | Name | Severity | Description |
|------|------|----------|-------------|
| SYS_7001 | Config Error | CRITICAL | Configuration error |
| SYS_7002 | Init Failed | CRITICAL | Initialization failed |
| SYS_7003 | Resource Exhausted | CRITICAL | System resource exhausted |

## Error Severity Levels

- **LOW**: Informational, non-critical
- **MEDIUM**: Warning, may affect functionality
- **HIGH**: Error, affects functionality
- **CRITICAL**: Critical error, may cause shutdown

## Error Categories

- **API_ERROR**: External API errors
- **NETWORK_ERROR**: Network connectivity issues
- **EXCHANGE_ERROR**: Exchange-specific errors
- **AI_ERROR**: AI-related errors
- **VALIDATION_ERROR**: Input validation failures
- **DATA_ERROR**: Data loading/saving issues
- **BUSINESS_LOGIC_ERROR**: Trading logic errors
- **SYSTEM_ERROR**: System-level errors

## Using Error Codes

Error codes are automatically assigned when using `log_error_with_context()`:

```python
from utils.error_handler import (
    log_error_with_context, ErrorCode, ErrorCategory, ErrorSeverity
)

try:
    # operation
except Exception as e:
    log_error_with_context(
        e, ErrorCode.API_TIMEOUT,
        ErrorCategory.API_ERROR, ErrorSeverity.HIGH,
        "ComponentName", symbol="BTC/USDT", operation="analyze"
    )
```

## Error Context

Every error includes:
- **error_id**: Unique identifier
- **timestamp**: When error occurred
- **error_code**: Error code
- **category**: Error category
- **severity**: Severity level
- **message**: Error message
- **component**: Component where error occurred
- **symbol**: Trading symbol (if applicable)
- **operation**: Operation being performed
- **metadata**: Additional context
- **stack_trace**: Full stack trace
- **causal_chain**: Chain of related errors

