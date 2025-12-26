"""
Storage and logging service for launch sniper.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import aiofiles

from modules.launch_sniper.config import LaunchSniperConfig
from modules.launch_sniper.core.events import (
    LaunchEvent, AIDecision, ValidationResult,
    ExecutionEvent, TradeResult
)

logger = logging.getLogger(__name__)


class LaunchSniperLogger:
    """Logger for launch sniper events."""
    
    def __init__(self):
        self.config = LaunchSniperConfig
        self.storage_dir = self.config.STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, event_type: str) -> Path:
        """Get file path for event type."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"{event_type}_{date_str}.jsonl"
        return self.storage_dir / filename
    
    async def log_launch_event(self, event: LaunchEvent):
        """Log launch event."""
        file_path = self._get_file_path("launch_events")
        record = {
            **event.to_dict(),
            'logged_at': datetime.utcnow().isoformat()
        }
        
        async with aiofiles.open(file_path, 'a') as f:
            await f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        logger.debug(f"Logged launch event: {event.event_id}")
    
    async def log_ai_decision(self, decision: AIDecision):
        """Log AI decision."""
        file_path = self._get_file_path("launch_ai_decisions")
        record = {
            **decision.to_dict(),
            'logged_at': datetime.utcnow().isoformat()
        }
        
        async with aiofiles.open(file_path, 'a') as f:
            await f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        logger.debug(f"Logged AI decision: {decision.decision_id}")
    
    async def log_validation_result(self, validation: ValidationResult):
        """Log validation result."""
        file_path = self._get_file_path("launch_validation_results")
        record = {
            **validation.to_dict(),
            'logged_at': datetime.utcnow().isoformat()
        }
        
        async with aiofiles.open(file_path, 'a') as f:
            await f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        logger.debug(f"Logged validation: {validation.validation_id}")
    
    async def log_execution_event(self, event: ExecutionEvent):
        """Log execution event."""
        file_path = self._get_file_path("launch_execution_events")
        record = {
            **event.to_dict(),
            'logged_at': datetime.utcnow().isoformat()
        }
        
        async with aiofiles.open(file_path, 'a') as f:
            await f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        logger.debug(f"Logged execution event: {event.execution_id}")
    
    async def log_trade_result(self, trade: TradeResult):
        """Log trade result."""
        file_path = self._get_file_path("launch_trades")
        record = {
            **trade.to_dict(),
            'logged_at': datetime.utcnow().isoformat()
        }
        
        async with aiofiles.open(file_path, 'a') as f:
            await f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        logger.info(f"Logged trade result: {trade.trade_id}, PnL: {trade.pnl_percent:.2f}%")

