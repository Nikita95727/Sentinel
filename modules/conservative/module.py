"""
Conservative trading strategy module.
Implements TradingModule interface.
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Use loguru for consistency with main bot
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.models import TradingModule, ModuleStatus, CoreContext
from modules.conservative.config import ConservativeConfig
from modules.conservative.execution.engine import TradingEngine
from modules.conservative.scheduler import ConservativeScheduler


class ConservativeModule(TradingModule):
    """Conservative trading strategy module."""
    
    def __init__(self, core_context: CoreContext):
        super().__init__(core_context)
        self.config = ConservativeConfig
        self.engine: Optional[TradingEngine] = None
        self.scheduler: Optional[ConservativeScheduler] = None
        self._initialized = False
    
    async def start(self):
        """Start the conservative trading module."""
        if self.status != ModuleStatus.STOPPED:
            logger.warning("Module already started")
            return
        
        self.status = ModuleStatus.STARTING
        logger.info("Starting conservative trading module...")
        
        try:
            # Initialize engine and scheduler
            await self._initialize()
            
            # Start scheduler
            if self.scheduler:
                self.scheduler.start()
            
            # Run initial screening after scheduler starts
            logger.info("Running initial screening...")
            await self.scheduler._run_daily_screening()
            
            self.status = ModuleStatus.RUNNING
            logger.info("Conservative module started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start conservative module: {e}", exc_info=True)
            self.status = ModuleStatus.ERROR
            raise
    
    async def stop(self):
        """Stop the conservative trading module."""
        if self.status == ModuleStatus.STOPPED:
            return
        
        self.status = ModuleStatus.STOPPING
        logger.info("Stopping conservative trading module...")
        
        try:
            # Stop scheduler
            if self.scheduler:
                self.scheduler.stop()
            
            # Shutdown engine
            if self.engine:
                await self.engine.shutdown()
            
            self.status = ModuleStatus.STOPPED
            logger.info("Conservative module stopped")
            
        except Exception as e:
            logger.error(f"Error stopping conservative module: {e}", exc_info=True)
            self.status = ModuleStatus.ERROR
    
    def healthcheck(self) -> ModuleStatus:
        """Check module health."""
        if self.status == ModuleStatus.RUNNING:
            # Additional health checks can be added here
            if self.engine and self.scheduler:
                return ModuleStatus.RUNNING
            return ModuleStatus.ERROR
        return self.status
    
    async def _initialize(self):
        """Initialize module components."""
        if self._initialized:
            return
        
        # Import here to avoid circular dependencies
        from providers.bybit import BybitProvider
        from providers.grok import GrokProvider
        from services.analyzer import Analyzer
        from services.risk_manager import RiskManager
        from services.analytics import Analytics
        from services.ai_optimizer import AIOptimizer
        from storage.state_manager import StateManager
        from services.sqlite_scheduler import SQLiteScheduler
        
        # Use exchange from core context (shared resource)
        exchange = self.core_context.exchange
        
        # Initialize AI provider
        ai_provider = GrokProvider(
            api_key=self.config.GROK_API_KEY,
            model=self.config.GROK_MODEL
        )
        
        # Initialize services
        analyzer = Analyzer()
        risk_manager = RiskManager(
            balance=self.config.TRADING_BALANCE,
            stop_loss_pct=self.config.STOP_LOSS_PCT,
            min_risk_reward=self.config.MIN_RISK_REWARD
        )
        
        # Use module-specific storage paths
        state_manager = StateManager(storage_path=str(self.config.TRADES_DIR))
        analytics = Analytics(storage_path=str(self.config.ANALYTICS_DIR))
        
        # AI Optimizer
        ai_optimizer = AIOptimizer(
            ai_provider=ai_provider,
            cache_ttl_minutes=self.config.AI_CACHE_TTL_MINUTES
        )
        
        # Initialize trading engine
        initial_symbols = [self.config.TRADING_SYMBOL]
        self.engine = TradingEngine(
            exchange=exchange,
            ai_provider=ai_provider,
            analyzer=analyzer,
            risk_manager=risk_manager,
            state_manager=state_manager,
            analytics=analytics,
            ai_optimizer=ai_optimizer,
            symbols=initial_symbols,
            timeframe=self.config.TRADING_TIMEFRAME,
            dry_run=self.config.DRY_RUN
        )
        
        await self.engine.initialize()
        
        # Initialize scheduler
        self.scheduler = ConservativeScheduler(
            engine=self.engine,
            analyzer=analyzer,
            ai_provider=ai_provider,
            exchange=exchange,
            config=self.config
        )
        
        self._initialized = True
        logger.info("Conservative module initialized")

