"""
Launch Sniper module implementing TradingModule interface.
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.models import TradingModule, ModuleStatus, CoreContext
from modules.launch_sniper.core.orchestrator import LaunchSniperOrchestrator
from modules.launch_sniper.config import LaunchSniperConfig

logger = logging.getLogger(__name__)


class LaunchSniperModule(TradingModule):
    """Launch sniper trading module."""
    
    def __init__(self, core_context: CoreContext):
        super().__init__(core_context)
        self.config = LaunchSniperConfig
        self.orchestrator: Optional[LaunchSniperOrchestrator] = None
        self._initialized = False
    
    async def start(self):
        """Start the launch sniper module."""
        if self.status != ModuleStatus.STOPPED:
            logger.warning("Module already started")
            return
        
        self.status = ModuleStatus.STARTING
        logger.info("Starting launch sniper module...")
        
        try:
            # Initialize orchestrator
            await self._initialize()
            
            # Run initial discovery
            await self.orchestrator.run_discovery_phase()
            
            self.status = ModuleStatus.RUNNING
            logger.info("Launch sniper module started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start launch sniper module: {e}", exc_info=True)
            self.status = ModuleStatus.ERROR
            raise
    
    async def stop(self):
        """Stop the launch sniper module."""
        if self.status == ModuleStatus.STOPPED:
            return
        
        self.status = ModuleStatus.STOPPING
        logger.info("Stopping launch sniper module...")
        
        try:
            if self.orchestrator:
                await self.orchestrator.close()
            
            self.status = ModuleStatus.STOPPED
            logger.info("Launch sniper module stopped")
            
        except Exception as e:
            logger.error(f"Error stopping launch sniper module: {e}", exc_info=True)
            self.status = ModuleStatus.ERROR
    
    def healthcheck(self) -> ModuleStatus:
        """Check module health."""
        if self.status == ModuleStatus.RUNNING:
            if self.orchestrator:
                return ModuleStatus.RUNNING
            return ModuleStatus.ERROR
        return self.status
    
    async def _initialize(self):
        """Initialize module components."""
        if self._initialized:
            return
        
        # Use exchange from core context (shared resource)
        # But launch sniper needs its own exchange instance for isolation
        # So we'll create a new one but use same credentials
        
        from providers.bybit import BybitProvider
        
        # Create new exchange instance for launch sniper (isolated)
        exchange = BybitProvider(
            api_key=self.core_context.config.get('bybit_api_key'),
            api_secret=self.core_context.config.get('bybit_api_secret'),
            testnet=self.core_context.config.get('bybit_testnet', True)
        )
        
        # Initialize orchestrator
        self.orchestrator = LaunchSniperOrchestrator()
        
        # Initialize orchestrator (it will create its own exchange instances)
        await self.orchestrator.initialize()
        
        # Note: Launch sniper uses its own exchange instances for isolation
        # This is intentional - launch sniper should be completely isolated
        
        self._initialized = True
        logger.info("Launch sniper module initialized")

