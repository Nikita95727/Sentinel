"""
Core application entry point.
Manages module lifecycle and shared resources.
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any

from loguru import logger
from core.models import CoreContext, TradingModule, ModuleStatus


class SentinelApp:
    """Main application orchestrator."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize application.
        
        Args:
            config: Global configuration dictionary
        """
        self.config = config
        self.modules: List[TradingModule] = []
        self.core_context: CoreContext = None
    
    async def initialize(self):
        """Initialize core context and shared resources."""
        # Initialize exchange (will be shared by modules)
        from providers.bybit import BybitProvider
        
        exchange = BybitProvider(
            api_key=self.config.get('bybit_api_key'),
            api_secret=self.config.get('bybit_api_secret'),
            testnet=self.config.get('bybit_testnet', True)
        )
        
        await exchange.initialize()
        
        # Create core context
        self.core_context = CoreContext(
            exchange=exchange,
            logger=logger,
            config=self.config
        )
        
        logger.info("Core application initialized")
        logger.info(f"Exchange initialized: testnet={self.config.get('bybit_testnet', True)}")
    
    def register_module(self, module: TradingModule):
        """Register a trading module."""
        self.modules.append(module)
        logger.info(f"Registered module: {module.__class__.__name__}")
    
    async def start_all(self):
        """Start all registered modules."""
        logger.info(f"Starting {len(self.modules)} modules...")
        
        for module in self.modules:
            module_name = module.__class__.__name__
            logger.info(f"Attempting to start module: {module_name}")
            try:
                await module.start()
                logger.info(f"Module {module_name} started successfully")
            except Exception as e:
                logger.error(f"Failed to start module {module_name}: {e}", exc_info=True)
                # Don't raise - continue with other modules
                # But log the error clearly
    
    async def stop_all(self):
        """Stop all registered modules."""
        logger.info(f"Stopping {len(self.modules)} modules...")
        
        for module in reversed(self.modules):  # Stop in reverse order
            try:
                await module.stop()
                logger.info(f"Module {module.__class__.__name__} stopped")
            except Exception as e:
                logger.error(f"Error stopping module {module.__class__.__name__}: {e}", exc_info=True)
    
    def healthcheck_all(self) -> Dict[str, ModuleStatus]:
        """Check health of all modules."""
        return {
            module.__class__.__name__: module.healthcheck()
            for module in self.modules
        }
    
    async def close(self):
        """Close shared resources."""
        if self.core_context and self.core_context.exchange:
            try:
                await self.core_context.exchange.close()
            except Exception as e:
                logger.error(f"Error closing exchange: {e}")

