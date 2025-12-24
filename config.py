"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    # Exchange Configuration
    bybit_api_key: str
    bybit_api_secret: str
    bybit_testnet: bool = False
    
    # AI Configuration
    grok_api_key: str
    grok_model: str = "grok-beta"
    
    # Trading Configuration
    trading_symbol: str = "BTC/USDT"  # Fallback если screening не сработал
    trading_timeframe: str = "30m"
    trading_balance: float = 10.0
    
    # Daily Screener Configuration
    screener_enabled: bool = True
    screener_interval_hours: int = 24
    screener_top_n: int = 20
    screener_max_symbols: int = 2
    
    # Risk Management
    stop_loss_pct: float = 2.0
    min_risk_reward: float = 1.5
    min_ai_confidence: float = 80.0
    
    # Scheduling
    cycle_interval_minutes: int = 30
    
    # System Configuration
    dry_run: bool = True
    log_level: str = "INFO"
    log_rotation: str = "100 MB"
    log_retention: str = "30 days"
    
    # Storage
    storage_path: str = "storage/trades.jsonl"  # JSONL format for Grok-friendly learning
    
    
# Global settings instance
settings = Settings()
