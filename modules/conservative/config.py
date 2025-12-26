"""
Configuration for conservative trading module.
"""
import os
from pathlib import Path
from typing import Optional

class ConservativeConfig:
    """Configuration for conservative trading module."""
    
    # Trading parameters
    TRADING_SYMBOL: str = os.getenv("TRADING_SYMBOL", "BTC/USDT")
    TRADING_TIMEFRAME: str = os.getenv("TRADING_TIMEFRAME", "30m")
    CYCLE_INTERVAL_MINUTES: int = int(os.getenv("CYCLE_INTERVAL_MINUTES", "120"))
    
    # Screening
    SCREENER_INTERVAL_HOURS: int = int(os.getenv("SCREENER_INTERVAL_HOURS", "48"))
    SCREENER_TOP_N: int = int(os.getenv("SCREENER_TOP_N", "20"))
    SCREENER_MAX_SYMBOLS: int = int(os.getenv("SCREENER_MAX_SYMBOLS", "1"))
    
    # Risk management
    TRADING_BALANCE: float = float(os.getenv("TRADING_BALANCE", "10.0"))
    STOP_LOSS_PCT: float = float(os.getenv("STOP_LOSS_PCT", "2.0"))
    MIN_RISK_REWARD: float = float(os.getenv("MIN_RISK_REWARD", "1.5"))
    
    # Storage (module-specific)
    STORAGE_DIR: Path = Path("storage/conservative")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Analytics storage (module-specific)
    ANALYTICS_DIR: Path = Path("storage/conservative/analytics")
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Trades storage (module-specific)
    TRADES_DIR: Path = Path("storage/conservative/trades")
    TRADES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Logging
    LOG_DIR: Path = Path("logs/conservative")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Dry run
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    
    # AI
    GROK_API_KEY: Optional[str] = os.getenv("GROK_API_KEY")
    GROK_MODEL: str = os.getenv("GROK_MODEL", "grok-beta")
    AI_CACHE_TTL_MINUTES: int = int(os.getenv("AI_CACHE_TTL_MINUTES", "30"))
    
    # Storage retention
    STORAGE_RETENTION_DAYS: int = int(os.getenv("STORAGE_RETENTION_DAYS", "30"))

