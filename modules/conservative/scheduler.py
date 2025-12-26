"""
Scheduler for conservative trading module.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from modules.conservative.config import ConservativeConfig
from modules.conservative.execution.engine import TradingEngine

logger = logging.getLogger(__name__)


class ConservativeScheduler:
    """Scheduler for conservative trading module."""
    
    def __init__(
        self,
        engine: TradingEngine,
        analyzer,
        ai_provider,
        exchange,
        config: ConservativeConfig
    ):
        self.engine = engine
        self.analyzer = analyzer
        self.ai_provider = ai_provider
        self.exchange = exchange
        self.config = config
        self.scheduler = AsyncIOScheduler()
        self._jobs_added = False
    
    def start(self):
        """Start scheduler and add jobs."""
        if self._jobs_added:
            logger.warning("Scheduler jobs already added")
            return
        
        # Add daily screening job
        self.scheduler.add_job(
            self._run_daily_screening,
            trigger=IntervalTrigger(hours=self.config.SCREENER_INTERVAL_HOURS),
            id='conservative_daily_screening',
            name='Conservative Daily Screening',
            replace_existing=True
        )
        
        # Add trading cycle job
        self.scheduler.add_job(
            self.engine.run_cycle,
            trigger=IntervalTrigger(minutes=self.config.CYCLE_INTERVAL_MINUTES),
            id='conservative_trading_cycle',
            name='Conservative Trading Cycle',
            replace_existing=True
        )
        
        # Add daily report job (if report_generator available)
        try:
            from services.report_generator import ReportGenerator
            from services.analytics import Analytics
            from storage.state_manager import StateManager
            
            analytics = Analytics(storage_path=str(self.config.ANALYTICS_DIR))
            state_manager = StateManager(storage_path=str(self.config.TRADES_DIR))
            report_generator = ReportGenerator(analytics=analytics, state_manager=state_manager)
            
            async def generate_daily_report_job():
                try:
                    report = await report_generator.generate_daily_report()
                    logger.info("\n" + report)
                except Exception as e:
                    logger.error(f"Error generating daily report: {e}")
            
            self.scheduler.add_job(
                generate_daily_report_job,
                trigger=CronTrigger(hour=0, minute=0),
                id='conservative_daily_report',
                name='Conservative Daily Report',
                replace_existing=True
            )
        except Exception as e:
            logger.debug(f"Daily report job not added: {e}")
        
        # Add SQLite synchronization job (if not dry run)
        if not self.config.DRY_RUN:
            try:
                from services.sqlite_scheduler import SQLiteScheduler
                from services.analytics import Analytics
                from storage.state_manager import StateManager
                
                analytics = Analytics(storage_path=str(self.config.ANALYTICS_DIR))
                state_manager = StateManager(storage_path=str(self.config.TRADES_DIR))
                sqlite_scheduler = SQLiteScheduler(
                    state_manager=state_manager,
                    analytics=analytics,
                    sync_time="00:30"  # 30 minutes after midnight (after file rotation)
                )
                
                async def sqlite_sync_job():
                    """Perform daily SQLite synchronization."""
                    try:
                        await sqlite_scheduler._daily_sync()
                        logger.info("SQLite synchronization completed")
                    except Exception as e:
                        logger.error(f"Error in SQLite sync job: {e}")
                
                self.scheduler.add_job(
                    sqlite_sync_job,
                    trigger=CronTrigger(hour=0, minute=30),  # 00:30 UTC (after file rotation)
                    id='conservative_sqlite_sync',
                    name='Conservative SQLite Synchronization',
                    replace_existing=True
                )
                logger.info("SQLite daily sync scheduled at 00:30 UTC")
            except Exception as e:
                logger.debug(f"SQLite sync job not added: {e}")
        
        # Add daily rotation job
        async def daily_rotation_job():
            try:
                await self.engine.state_manager.perform_daily_rotation()
                logger.info("Daily file rotation completed")
            except Exception as e:
                logger.error(f"Error in daily rotation job: {e}")
        
        self.scheduler.add_job(
            daily_rotation_job,
            trigger=CronTrigger(hour=0, minute=0),
            id='conservative_daily_rotation',
            name='Conservative Daily Rotation',
            replace_existing=True
        )
        
        # Add old files cleanup job (runs once per day at 1 AM UTC)
        async def cleanup_old_files_job():
            """Clean up old trade files based on retention policy."""
            try:
                retention_days = self.config.STORAGE_RETENTION_DAYS
                await self.engine.state_manager.cleanup_old_files(retention_days=retention_days)
                logger.info(f"Old files cleanup completed (retention: {retention_days} days)")
            except Exception as e:
                logger.error(f"Error in cleanup job: {e}")
        
        self.scheduler.add_job(
            cleanup_old_files_job,
            trigger=CronTrigger(hour=1, minute=0),  # 1 AM UTC (after rotation)
            id='conservative_cleanup_old_files',
            name='Conservative Old Files Cleanup',
            replace_existing=True
        )
        
        # Start scheduler
        self.scheduler.start()
        self._jobs_added = True
        logger.info(
            f"Conservative scheduler started: "
            f"Screening every {self.config.SCREENER_INTERVAL_HOURS}h, "
            f"Trading every {self.config.CYCLE_INTERVAL_MINUTES}min"
        )
    
    def stop(self):
        """Stop scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Conservative scheduler stopped")
    
    async def _run_daily_screening(self):
        """Run daily screening job."""
        from modules.conservative.screening import run_daily_screening
        
        await run_daily_screening(
            engine=self.engine,
            analyzer=self.analyzer,
            ai_provider=self.ai_provider,
            exchange=self.exchange
        )

