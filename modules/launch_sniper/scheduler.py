"""
Scheduler for launch sniper - runs discovery periodically.
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from modules.launch_sniper.core.orchestrator import LaunchSniperOrchestrator
from modules.launch_sniper.config import LaunchSniperConfig

logger = logging.getLogger(__name__)


class LaunchSniperScheduler:
    """Scheduler for launch sniper."""
    
    def __init__(self):
        self.config = LaunchSniperConfig
        self.scheduler = AsyncIOScheduler()
        self.orchestrator = LaunchSniperOrchestrator()
        self.initialized = False
    
    async def initialize(self):
        """Initialize orchestrator."""
        if not self.initialized:
            await self.orchestrator.initialize()
            self.initialized = True
    
    async def discovery_job(self):
        """Discovery job - runs periodically."""
        logger.info("Running scheduled discovery...")
        try:
            events = await self.orchestrator.run_discovery_phase()
            
            # Process new events
            for event in events:
                await self.orchestrator.process_event(event)
                
        except Exception as e:
            logger.error(f"Error in discovery job: {e}", exc_info=True)
    
    def start(self):
        """Start scheduler."""
        if not self.initialized:
            raise RuntimeError("Scheduler not initialized. Call initialize() first.")
        
        # Schedule discovery job
        self.scheduler.add_job(
            self.discovery_job,
            trigger=IntervalTrigger(hours=self.config.DISCOVERY_INTERVAL_HOURS),
            id='discovery_job',
            name='Launch Discovery',
            replace_existing=True
        )
        
        # Start scheduler
        self.scheduler.start()
        logger.info(f"Scheduler started - discovery every {self.config.DISCOVERY_INTERVAL_HOURS} hours")
    
    def stop(self):
        """Stop scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    async def close(self):
        """Close orchestrator."""
        await self.orchestrator.close()

