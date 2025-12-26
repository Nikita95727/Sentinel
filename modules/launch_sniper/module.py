"""
Launch Sniper module implementing TradingModule interface.
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from core.models import TradingModule, ModuleStatus, CoreContext
from modules.launch_sniper.core.orchestrator import LaunchSniperOrchestrator
from modules.launch_sniper.config import LaunchSniperConfig


class LaunchSniperModule(TradingModule):
    """Launch sniper trading module."""
    
    def __init__(self, core_context: CoreContext):
        super().__init__(core_context)
        self.config = LaunchSniperConfig
        self.orchestrator: Optional[LaunchSniperOrchestrator] = None
        self._initialized = False
    
    async def start(self):
        """Start the launch sniper module."""
        logger.info("=" * 80)
        logger.info("LAUNCH SNIPER MODULE - START")
        logger.info("=" * 80)
        
        if self.status != ModuleStatus.STOPPED:
            logger.warning(f"Module already started (status: {self.status})")
            return
        
        self.status = ModuleStatus.STARTING
        logger.info("Starting launch sniper module...")
        logger.info(f"Module status: {self.status}")
        
        try:
            logger.info("Step 1: Initializing orchestrator...")
            # Initialize orchestrator
            await self._initialize()
            logger.info("✅ Orchestrator initialized")
            
            logger.info("Step 2: Running discovery phase...")
            # Run initial discovery
            events = await self.orchestrator.run_discovery_phase()
            logger.info(f"✅ Discovery complete: {len(events)} events found")
            
            self.status = ModuleStatus.RUNNING
            logger.info("=" * 80)
            logger.info("✅ Launch sniper module started successfully")
            logger.info(f"Status: {self.status}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ Failed to start launch sniper module: {e}")
            logger.error("=" * 80, exc_info=True)
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
            logger.info("Module already initialized, skipping...")
            return
        
        logger.info("Initializing launch sniper module components...")
        
        try:
            # Initialize orchestrator
            logger.info("Creating LaunchSniperOrchestrator instance...")
            self.orchestrator = LaunchSniperOrchestrator()
            logger.info("✅ Orchestrator instance created")
            
            # Initialize orchestrator (it will create its own exchange instances)
            logger.info("Initializing orchestrator services...")
            await self.orchestrator.initialize()
            logger.info("✅ Orchestrator services initialized")
            
            self._initialized = True
            logger.info("✅ Launch sniper module initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize launch sniper module: {e}", exc_info=True)
            raise

