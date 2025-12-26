"""
Orchestrator for launch sniper - coordinates all phases.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from modules.launch_sniper.core.events import LaunchEvent, AIDecision, ValidationResult, TradeResult
from modules.launch_sniper.core.fsm import ExecutionFSM, ExecutionState
from modules.launch_sniper.services.discovery import DiscoveryService
from modules.launch_sniper.services.ai_analyzer import AIAnalyzer
from modules.launch_sniper.services.validator import ValidationService
from modules.launch_sniper.services.arming import ArmingService
from modules.launch_sniper.services.executor import ExecutionService
from modules.launch_sniper.storage.logger import LaunchSniperLogger
from modules.launch_sniper.config import LaunchSniperConfig

logger = logging.getLogger(__name__)


class LaunchSniperOrchestrator:
    """Main orchestrator for launch sniper."""
    
    def __init__(self):
        self.config = LaunchSniperConfig
        self.discovery = DiscoveryService()
        self.ai_analyzer = AIAnalyzer()
        self.validator = ValidationService()
        self.arming = ArmingService()
        self.executor = ExecutionService()
        self.logger = LaunchSniperLogger()
        
        # Active events being tracked
        self.active_events: Dict[str, LaunchEvent] = {}
        self.active_fsms: Dict[str, ExecutionFSM] = {}
    
    async def initialize(self):
        """Initialize all services."""
        logger.info("Initializing Launch Sniper Orchestrator...")
        try:
            logger.info("  - Initializing DiscoveryService...")
            await self.discovery.initialize()
            logger.info("  ✅ DiscoveryService initialized")
            
            logger.info("  - Initializing AIAnalyzer...")
            await self.ai_analyzer.initialize()
            logger.info("  ✅ AIAnalyzer initialized")
            
            logger.info("  - Initializing ArmingService...")
            await self.arming.initialize()
            logger.info("  ✅ ArmingService initialized")
            
            logger.info("  - Initializing ExecutionService...")
            await self.executor.initialize()
            logger.info("  ✅ ExecutionService initialized")
            
            logger.info("✅ Launch sniper orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize orchestrator: {e}", exc_info=True)
            raise
    
    async def run_discovery_phase(self) -> List[LaunchEvent]:
        """
        Phase A: Discover new listing events.
        
        Returns:
            List of discovered launch events
        """
        logger.info("Starting discovery phase...")
        events = await self.discovery.discover_listings()
        
        for event in events:
            await self.logger.log_launch_event(event)
            self.active_events[event.event_id] = event
            logger.info(f"Discovered: {event.symbol} at {event.listing_time}")
        
        logger.info(f"Discovery complete: {len(events)} events found")
        return events
    
    async def run_ai_analysis_phase(self, event: LaunchEvent) -> AIDecision:
        """
        Phase B: AI context analysis.
        
        IMPORTANT: AI only provides context, not trading decision.
        
        Args:
            event: Launch event to analyze
            
        Returns:
            AI decision (for context only)
        """
        logger.info(f"Starting AI analysis for {event.symbol}...")
        
        # Gather market data (placeholder - implement based on available APIs)
        market_data = await self._gather_market_data(event)
        
        # Call AI analyzer
        ai_decision = await self.ai_analyzer.analyze_launch_event(event, market_data)
        
        # Log AI decision
        await self.logger.log_ai_decision(ai_decision)
        
        logger.info(f"AI analysis complete: {ai_decision.classification} (confidence: {ai_decision.confidence})")
        return ai_decision
    
    async def run_validation_phase(
        self,
        event: LaunchEvent,
        ai_decision: Optional[AIDecision] = None
    ) -> ValidationResult:
        """
        Phase C: Deterministic validation.
        
        IMPORTANT: This is where GO/ABORT decision is made.
        AI decision is NOT used - only for context.
        
        Args:
            event: Launch event
            ai_decision: AI decision (for context only)
            
        Returns:
            Validation result with GO or ABORT_REASON_*
        """
        logger.info(f"Starting validation for {event.symbol}...")
        
        # Gather market data
        market_data = await self._gather_market_data(event)
        
        # Validate (AI decision passed for context, but not used in validation)
        validation = await self.validator.validate_launch(event, ai_decision, market_data)
        
        # Log validation result
        await self.logger.log_validation_result(validation)
        
        logger.info(f"Validation complete: {validation.decision}")
        return validation
    
    async def run_arming_phase(
        self,
        event: LaunchEvent,
        validation: ValidationResult
    ) -> Dict[str, Any]:
        """
        Phase D: Arming before listing start.
        
        Args:
            event: Launch event
            validation: Validation result (must be GO)
            
        Returns:
            Arming result with trade plan
        """
        if validation.decision != "GO":
            logger.warning(f"Skipping arming - validation failed: {validation.decision}")
            return {'error': f"Validation failed: {validation.decision}"}
        
        logger.info(f"Starting arming for {event.symbol}...")
        
        # Create FSM
        fsm = ExecutionFSM(event.event_id, event.symbol, event.listing_time)
        self.active_fsms[event.event_id] = fsm
        
        # Arm
        arming_result = await self.arming.arm_for_listing(event, validation, fsm)
        
        # Log execution event
        await self.logger.log_execution_event(
            ExecutionEvent(
                event_id=event.event_id,
                phase="ARMING",
                state=fsm.get_state().value,
                action_taken="ARM",
                execution_result="SUCCESS" if not arming_result.get('errors') else "FAILED",
                metadata=arming_result
            )
        )
        
        logger.info(f"Arming complete: {fsm.get_state().value}")
        return arming_result
    
    async def run_execution_phase(
        self,
        event: LaunchEvent,
        trade_plan: Dict[str, Any]
    ) -> TradeResult:
        """
        Phase E + F: Execute trade and exit.
        
        Args:
            event: Launch event
            trade_plan: Trade plan from arming phase
            
        Returns:
            Trade result
        """
        logger.info(f"Starting execution for {event.symbol}...")
        
        fsm = self.active_fsms.get(event.event_id)
        if not fsm:
            fsm = ExecutionFSM(event.event_id, event.symbol, event.listing_time)
            self.active_fsms[event.event_id] = fsm
        
        # Execute
        execution_events = await self.executor.execute_trade_plan(fsm, trade_plan)
        
        # Log all execution events
        for exec_event in execution_events:
            await self.logger.log_execution_event(exec_event)
        
        # Create trade result
        trade_result = TradeResult(
            event_id=event.event_id,
            symbol=event.symbol,
            entry_price=fsm.ctx.entry_price,
            exit_price=fsm.ctx.exit_price,
            position_size=fsm.ctx.position_size,
            pnl_usdt=fsm.ctx.pnl_usdt,
            pnl_percent=fsm.ctx.pnl_percent,
            entry_time=fsm.ctx.state_entered_at if fsm.ctx.position_size > 0 else None,
            exit_time=datetime.utcnow() if fsm.get_state() == ExecutionState.DONE else None,
            exit_reason=fsm.ctx.abort_reason or "COMPLETED",
            execution_events=execution_events
        )
        
        # Log trade result
        await self.logger.log_trade_result(trade_result)
        
        logger.info(f"Execution complete: PnL {trade_result.pnl_percent:.2f}%")
        return trade_result
    
    async def process_event(self, event: LaunchEvent) -> Optional[TradeResult]:
        """
        Process a single launch event through all phases.
        
        Args:
            event: Launch event to process
            
        Returns:
            Trade result if executed, None otherwise
        """
        try:
            # Phase B: AI Analysis
            ai_decision = await self.run_ai_analysis_phase(event)
            
            # Phase C: Validation
            validation = await self.run_validation_phase(event, ai_decision)
            
            if validation.decision != "GO":
                logger.info(f"Event {event.symbol} aborted: {validation.decision}")
                return None
            
            # Phase D: Arming
            arming_result = await self.run_arming_phase(event, validation)
            
            if arming_result.get('errors'):
                logger.warning(f"Arming failed for {event.symbol}: {arming_result['errors']}")
                return None
            
            trade_plan = arming_result.get('trade_plan', {})
            
            # Phase E + F: Execution
            trade_result = await self.run_execution_phase(event, trade_plan)
            
            return trade_result
            
        except Exception as e:
            logger.error(f"Error processing event {event.symbol}: {e}")
            return None
    
    async def monitor_active_events(self):
        """Monitor active events and trigger arming/execution at right times."""
        while True:
            now = datetime.utcnow()
            
            for event_id, event in list(self.active_events.items()):
                time_until_listing = (event.listing_time - now).total_seconds() / 60
                
                # Check if time to arm
                if (self.config.ARMING_TIME_MINUTES - 1) <= time_until_listing <= (self.config.ARMING_TIME_MINUTES + 1):
                    if event_id not in self.active_fsms:
                        # Run validation and arming
                        ai_decision = await self.run_ai_analysis_phase(event)
                        validation = await self.run_validation_phase(event, ai_decision)
                        
                        if validation.decision == "GO":
                            await self.run_arming_phase(event, validation)
                
                # Check if listing time reached
                if time_until_listing <= 0 and event_id in self.active_fsms:
                    fsm = self.active_fsms[event_id]
                    if fsm.get_state() == ExecutionState.ARMED:
                        # Execution will be handled by executor
                        pass
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def _gather_market_data(self, event: LaunchEvent) -> Dict[str, Any]:
        """Gather market data for event."""
        # Placeholder - implement based on available APIs
        # Could include: CoinMarketCap, Bybit pre-market data, etc.
        return {
            'symbol': event.symbol,
            'source': 'placeholder'
        }
    
    async def close(self):
        """Close all services."""
        await self.discovery.close()
        await self.arming.close()
        await self.executor.close()

