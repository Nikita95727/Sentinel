"""
Scheduled SQLite synchronization service.
Runs daily sync to keep SQLite database up-to-date with minimal server load.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from typing import Optional


class SQLiteScheduler:
    """
    Schedules daily SQLite synchronization to minimize server load.
    Syncs once per day at midnight UTC.
    """
    
    def __init__(
        self,
        state_manager,
        analytics,
        sync_time: str = "00:00"  # HH:MM format, UTC
    ):
        """
        Initialize SQLite scheduler.
        
        Args:
            state_manager: StateManager instance
            analytics: Analytics instance
            sync_time: Time to run sync daily (HH:MM format, UTC)
        """
        self.state_manager = state_manager
        self.analytics = analytics
        self.sync_time = sync_time
        self.scheduler: Optional[AsyncIOScheduler] = None
    
    def start(self):
        """Start the scheduler."""
        if self.scheduler and self.scheduler.running:
            logger.warning("SQLite scheduler already running")
            return
        
        self.scheduler = AsyncIOScheduler()
        
        # Parse sync time
        hour, minute = map(int, self.sync_time.split(':'))
        
        # Schedule daily sync at specified time (UTC)
        self.scheduler.add_job(
            self._daily_sync,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='sqlite_daily_sync',
            name='Daily SQLite synchronization',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info(f"SQLite scheduler started - daily sync at {self.sync_time} UTC")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("SQLite scheduler stopped")
    
    async def _daily_sync(self):
        """Perform daily SQLite synchronization."""
        try:
            logger.info("Starting daily SQLite synchronization...")
            
            # Sync trades
            trades_count = await self.state_manager.sync_to_sqlite()
            
            # Sync analytics
            analytics_counts = await self.analytics.sync_to_sqlite()
            
            total = trades_count + sum(analytics_counts.values())
            logger.success(
                f"Daily SQLite sync completed: "
                f"{trades_count} trades, "
                f"{sum(analytics_counts.values())} analytics events "
                f"(total: {total})"
            )
            
        except Exception as e:
            logger.error(f"Error during daily SQLite sync: {e}", exc_info=True)
    
    async def sync_now(self):
        """Manually trigger sync immediately (for testing)."""
        await self._daily_sync()


