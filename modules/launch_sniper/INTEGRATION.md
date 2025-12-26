# Integration Guide

## 🔒 Complete Isolation

The launch sniper module is **completely isolated** from the main trading bot:

### Separate Components
- ✅ Own folder: `modules/launch_sniper/`
- ✅ Own config: `modules/launch_sniper/config.py`
- ✅ Own storage: `storage/launch_sniper/`
- ✅ Own logs: `logs/launch_sniper/`
- ✅ Own scheduler: `modules/launch_sniper/scheduler.py`
- ✅ Own main entry: `modules/launch_sniper/main.py`

### No Interference
- ❌ Does NOT share risk management
- ❌ Does NOT share balance
- ❌ Does NOT share trade history
- ❌ Does NOT affect main bot's decisions
- ❌ Does NOT use main bot's scheduler

### Shared Resources (Read-Only)
- ✅ Uses same Bybit API keys (separate connection)
- ✅ Uses same Grok API key (separate calls)
- ✅ Uses same logging infrastructure (separate files)

---

## 🚀 Running the Module

### Option 1: Standalone

```bash
# Run once
python -m modules.launch_sniper.main

# Or with scheduler (runs discovery periodically)
python -m modules.launch_sniper.scheduler
```

### Option 2: Integration with Main Bot (Optional)

If you want to run both bots together, you can:

1. **Separate Processes** (Recommended)
   ```bash
   # Terminal 1: Main bot
   python main.py
   
   # Terminal 2: Launch sniper
   python -m launch_sniper.main
   ```

2. **Same Process** (Not Recommended)
   - Import launch sniper scheduler into main.py
   - Add to main bot's scheduler
   - **Warning**: This reduces isolation

---

## 📊 Data Separation

### Main Bot Data
- `storage/trades/trades_*.jsonl`
- `storage/analytics/ai_decisions_*.jsonl`
- `storage/analytics/market_conditions_*.jsonl`

### Launch Sniper Data
- `storage/launch_sniper/launch_events_*.jsonl`
- `storage/launch_sniper/launch_ai_decisions_*.jsonl`
- `storage/launch_sniper/launch_validation_results_*.jsonl`
- `storage/launch_sniper/launch_execution_events_*.jsonl`
- `storage/launch_sniper/launch_trades_*.jsonl`

**No overlap, no conflicts.**

---

## ⚙️ Configuration

### Environment Variables

```bash
# Required
export BYBIT_API_KEY="your_key"
export BYBIT_API_SECRET="your_secret"

# Optional (for AI analysis)
export GROK_API_KEY="your_grok_key"

# Safety (recommended)
export LAUNCH_SNIPER_DRY_RUN="true"
export BYBIT_TESTNET="true"
```

### Config File

Edit `launch_sniper/config.py` for advanced settings:
- Budget limits
- Timing parameters
- Exit logic
- Circuit breakers

---

## 🔍 Monitoring

### Check Logs

```bash
# Launch sniper logs
tail -f logs/launch_sniper/*.log

# Data files
ls -lh storage/launch_sniper/
```

### Check Status

The module logs all phases:
- Discovery events
- AI decisions
- Validation results
- Execution events
- Trade results

---

## 🛡️ Safety

1. **Dry Run Mode** (default: enabled)
   - Simulates all trades
   - No real execution
   - Safe for testing

2. **Testnet** (recommended)
   - Use Bybit testnet
   - No real money at risk

3. **Budget Limits**
   - Min: $5
   - Max: $50 per launch
   - Configurable

4. **Circuit Breakers**
   - Automatic exit on spread/liquidity issues
   - Time-based exit
   - Stop loss

---

## 📝 Important Notes

1. **This is experimental** - Use at your own risk
2. **High risk strategy** - Not for production trading
3. **R&D focus** - Designed for data collection
4. **Complete isolation** - Won't affect main bot
5. **Dry run recommended** - Test thoroughly first

---

**Version:** 1.0.0  
**Status:** Experimental

