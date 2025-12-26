# Launch Sniper Module

**High-risk event-driven listing sniper for Bybit spot.**

⚠️ **WARNING:** This is a high-risk, experimental module. Use at your own risk.

---

## 🎯 Purpose

This module implements a launch sniper strategy:
- Buys new tokens in the first seconds after listing starts
- Exits quickly (30-120 seconds)
- Fully isolated from main trading bot
- R&D focused - collects unique dataset

---

## 🏗️ Architecture

### Complete Isolation
- Separate folder: `modules/launch_sniper/`
- Separate config
- Separate logs and datasets
- Does NOT affect main bot

### Phase-Based Design

1. **Phase A - Discovery**
   - Finds new listing announcements
   - Creates launch events

2. **Phase B - AI Analysis**
   - Grok analyzes event context
   - Classification: HYPE / NEUTRAL / SUSPICIOUS
   - **AI does NOT make trading decisions**

3. **Phase C - Validation**
   - Deterministic mathematical filters
   - GO / ABORT_REASON_* decision
   - **This is where trading decision is made**

4. **Phase D - Arming**
   - Prepares before listing start (T-30min)
   - Creates static trade plan
   - **No AI calls**

5. **Phase E - Execution**
   - FSM-based execution
   - Places ladder orders
   - **No AI calls, only deterministic logic**

6. **Phase F - Exit**
   - Time-based exit (30-120 sec)
   - TP levels, stop loss
   - Circuit breakers
   - **No AI calls**

---

## 📊 Data Logging

All events logged to JSONL files:
- `launch_events_YYYY-MM-DD.jsonl`
- `launch_ai_decisions_YYYY-MM-DD.jsonl`
- `launch_validation_results_YYYY-MM-DD.jsonl`
- `launch_execution_events_YYYY-MM-DD.jsonl`
- `launch_trades_YYYY-MM-DD.jsonl`

Each record contains:
- `event_id` - Unique identifier
- `timestamp` - When event occurred
- `phase` - Which phase
- `decision` - What was decided
- `reasoning` - Why (for AI decisions)
- `validated_facts` - Mathematical facts (for validation)
- `action_taken` - What actually happened
- `execution_result` - Final result

---

## 🚀 Usage

### Standalone Mode

```bash
# Run once
python -m modules.launch_sniper.main

# Or with scheduler
python -m modules.launch_sniper.scheduler
```

### Configuration

Set environment variables:
```bash
export BYBIT_API_KEY="your_key"
export BYBIT_API_SECRET="your_secret"
export GROK_API_KEY="your_grok_key"  # Optional
export LAUNCH_SNIPER_DRY_RUN="true"  # Recommended for testing
```

Or edit `launch_sniper/config.py` directly.

---

## ⚙️ Configuration

Key parameters in `config.py`:

- `MIN_BUDGET_USDT`: Minimum budget (default: $5)
- `MAX_BUDGET_USDT`: Maximum budget (default: $50)
- `ARMING_TIME_MINUTES`: When to arm before listing (default: 30)
- `EXIT_TIME_SECONDS`: Max time in position (default: 120)
- `TAKE_PROFIT_STEPS`: TP levels (default: [5%, 10%, 20%])
- `STOP_LOSS_PCT`: Hard stop (default: 10%)

---

## 🔒 Safety Features

1. **Dry Run Mode** (default: enabled)
   - Simulates trades without real execution
   - Safe for testing

2. **Circuit Breakers**
   - Spread > 5% → Exit
   - Liquidity drop > 50% → Exit
   - Time limit → Exit

3. **Validation Layer**
   - Multiple checks before execution
   - Budget limits
   - Price limits
   - Liquidity checks

4. **FSM Execution**
   - State machine prevents invalid transitions
   - Clear abort conditions

---

## 📝 Important Notes

1. **AI Role**: AI only provides context, NOT trading decisions
2. **Validation**: Only deterministic validation makes GO/ABORT decisions
3. **Execution**: No AI calls during execution
4. **Isolation**: Completely separate from main bot
5. **R&D Focus**: Designed for data collection, not profit optimization

---

## 🐛 Known Limitations

1. **Bybit API**: Listing announcements API may not be directly available
   - May need to parse website or use alternative methods
   - Discovery service is a placeholder

2. **Market Data**: Pre-market data gathering needs implementation
   - CoinMarketCap integration
   - Bybit pre-market data (if available)

3. **WebSocket**: Currently uses REST API
   - WebSocket can be added for faster execution

---

## 📚 Integration with Main Bot

This module:
- ✅ Uses same GrokProvider (if available)
- ✅ Uses same Bybit exchange connection
- ✅ Uses same logging infrastructure
- ❌ Does NOT share risk management
- ❌ Does NOT share balance
- ❌ Does NOT interfere with main bot

---

**Version:** 1.0.0  
**Status:** Experimental / R&D

