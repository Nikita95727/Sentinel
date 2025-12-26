"""
Configuration for Launch Sniper module.
"""
import os
from typing import Optional
from pathlib import Path

class LaunchSniperConfig:
    """Configuration for launch sniper module."""
    
    # Bybit API - try both naming conventions
    BYBIT_API_KEY: Optional[str] = os.getenv("BYBIT_API_KEY") or os.getenv("bybit_api_key")
    BYBIT_API_SECRET: Optional[str] = os.getenv("BYBIT_API_SECRET") or os.getenv("bybit_api_secret")
    BYBIT_TESTNET: bool = (
        os.getenv("BYBIT_TESTNET", os.getenv("bybit_testnet", "true"))
    ).lower() == "true"
    
    # Grok AI
    GROK_API_KEY: Optional[str] = os.getenv("GROK_API_KEY")
    
    # Discovery Phase
    DISCOVERY_INTERVAL_HOURS: int = 24  # Check for new listings once per day
    LISTING_WINDOW_HOURS: int = 72  # Only track listings within 72h
    
    # AI Analysis Phase
    AI_ENABLED: bool = True
    AI_MIN_CONFIDENCE: float = 0.0  # AI only provides context, not decision
    
    # Validation Phase
    MIN_BUDGET_USDT: float = 5.0  # Minimum budget for sniper
    MAX_BUDGET_USDT: float = 50.0  # Maximum budget per launch
    MAX_SPREAD_PCT: float = 2.0  # Maximum acceptable spread
    MIN_LIQUIDITY_USDT: float = 1000.0  # Minimum expected liquidity
    
    # Arming Phase
    ARMING_TIME_MINUTES: int = 30  # Start arming T-30 minutes before listing
    
    # Execution Phase
    ENTRY_LADDER_COUNT: int = 3  # Number of limit orders in ladder
    ENTRY_TIMEOUT_SECONDS: int = 10  # Max time to enter position
    MAX_POSITION_SIZE_USDT: float = 50.0
    
    # Exit Phase
    EXIT_TIME_MINUTES: int = 2  # Max time in position (2 minutes)
    EXIT_TIME_SECONDS: int = 120  # Alternative: 120 seconds
    TAKE_PROFIT_STEPS: list = [0.05, 0.10, 0.20]  # 5%, 10%, 20% TP levels
    STOP_LOSS_PCT: float = 0.10  # 10% hard stop
    CIRCUIT_BREAKER_SPREAD_PCT: float = 5.0  # Exit if spread > 5%
    CIRCUIT_BREAKER_LIQUIDITY_DROP_PCT: float = 0.5  # Exit if liquidity drops 50%
    
    # Storage
    STORAGE_DIR: Path = Path("storage/launch_sniper")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Logging
    LOG_DIR: Path = Path("logs/launch_sniper")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Dry run
    DRY_RUN: bool = os.getenv("LAUNCH_SNIPER_DRY_RUN", "true").lower() == "true"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        if not cls.BYBIT_API_KEY or not cls.BYBIT_API_SECRET:
            return False
        if cls.AI_ENABLED and not cls.GROK_API_KEY:
            return False
        return True

