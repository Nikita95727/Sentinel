"""
Common data models and interfaces.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ModuleStatus(Enum):
    """Module status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class CoreContext:
    """Shared context for all modules."""
    exchange: Any  # Exchange interface
    logger: Any  # Logger
    config: Dict[str, Any]  # Global config


class TradingModule(ABC):
    """Base interface for trading modules."""
    
    def __init__(self, core_context: CoreContext):
        self.core_context = core_context
        self.status = ModuleStatus.STOPPED
    
    @abstractmethod
    async def start(self):
        """Start the module."""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the module."""
        pass
    
    @abstractmethod
    def healthcheck(self) -> ModuleStatus:
        """Check module health."""
        pass
    
    def get_status(self) -> ModuleStatus:
        """Get current status."""
        return self.status

