"""
Phase D: Arming - Prepare for listing start.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import ccxt.async_support as ccxt

from modules.launch_sniper.core.events import LaunchEvent, ValidationResult
from modules.launch_sniper.core.fsm import ExecutionFSM, ExecutionState
from modules.launch_sniper.config import LaunchSniperConfig

logger = logging.getLogger(__name__)


class ArmingService:
    """Service for arming before listing start."""
    
    def __init__(self):
        self.config = LaunchSniperConfig
        self.exchange: Optional[ccxt.bybit] = None
    
    async def initialize(self):
        """Initialize exchange connection."""
        try:
            self.exchange = ccxt.bybit({
                'apiKey': self.config.BYBIT_API_KEY,
                'secret': self.config.BYBIT_API_SECRET,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'test': self.config.BYBIT_TESTNET
                }
            })
            logger.info("Arming service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize arming service: {e}")
            raise
    
    async def arm_for_listing(
        self,
        event: LaunchEvent,
        validation: ValidationResult,
        fsm: ExecutionFSM
    ) -> Dict[str, Any]:
        """
        Arm for listing start.
        
        This happens T-30 minutes before listing.
        No AI calls - only deterministic checks.
        
        Args:
            event: Launch event
            validation: Validation result
            fsm: Execution FSM
            
        Returns:
            Arming result with checks and trade plan
        """
        if not self.exchange:
            await self.initialize()
        
        arming_result = {
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {},
            'trade_plan': {},
            'errors': []
        }
        
        try:
            # Check 1: Verify listing time
            time_until_listing = (event.listing_time - datetime.utcnow()).total_seconds() / 60
            arming_result['checks']['time_until_listing_minutes'] = time_until_listing
            
            if time_until_listing < 0:
                arming_result['errors'].append("Listing already started")
                fsm.transition_to(ExecutionState.ABORT, "Listing already started")
                return arming_result
            
            if time_until_listing > self.config.ARMING_TIME_MINUTES + 10:
                arming_result['errors'].append(f"Too early to arm (T-{time_until_listing:.1f}min)")
                return arming_result
            
            # Check 2: Verify symbol exists
            try:
                markets = await self.exchange.load_markets(reload=True)
                if event.trading_pair not in markets:
                    arming_result['errors'].append(f"Symbol {event.trading_pair} not found")
                    fsm.transition_to(ExecutionState.ABORT, "Symbol not found")
                    return arming_result
                
                market = markets[event.trading_pair]
                arming_result['checks']['symbol_exists'] = True
                arming_result['checks']['price_precision'] = market.get('precision', {}).get('price', 8)
                arming_result['checks']['amount_precision'] = market.get('precision', {}).get('amount', 8)
                arming_result['checks']['min_amount'] = market.get('limits', {}).get('amount', {}).get('min', 0)
            except Exception as e:
                arming_result['errors'].append(f"Failed to verify symbol: {e}")
                fsm.transition_to(ExecutionState.ABORT, f"Symbol verification failed: {e}")
                return arming_result
            
            # Check 3: Verify balance
            try:
                balance = await self.exchange.fetch_balance()
                usdt_balance = balance.get('USDT', {}).get('free', 0.0)
                arming_result['checks']['usdt_balance'] = usdt_balance
                
                if usdt_balance < self.config.MIN_BUDGET_USDT:
                    arming_result['errors'].append(f"Insufficient balance: {usdt_balance} USDT")
                    fsm.transition_to(ExecutionState.ABORT, "Insufficient balance")
                    return arming_result
            except Exception as e:
                arming_result['errors'].append(f"Failed to check balance: {e}")
                fsm.transition_to(ExecutionState.ABORT, f"Balance check failed: {e}")
                return arming_result
            
            # Check 4: Prepare WebSocket (if needed)
            # For now, we'll use REST API, but WebSocket can be added later
            arming_result['checks']['websocket_ready'] = False  # Placeholder
            
            # Create trade plan
            trade_plan = self._create_trade_plan(event, validation, arming_result['checks'])
            arming_result['trade_plan'] = trade_plan
            
            # Transition to ARMED state
            if not arming_result['errors']:
                fsm.transition_to(ExecutionState.ARMED, "Armed and ready")
                logger.info(f"Armed for {event.symbol} at {event.listing_time}")
            
        except Exception as e:
            logger.error(f"Error during arming: {e}")
            arming_result['errors'].append(str(e))
            fsm.transition_to(ExecutionState.ABORT, f"Arming failed: {e}")
        
        return arming_result
    
    def _create_trade_plan(
        self,
        event: LaunchEvent,
        validation: ValidationResult,
        checks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create static trade plan."""
        budget = min(
            self.config.MAX_BUDGET_USDT,
            checks.get('usdt_balance', self.config.MIN_BUDGET_USDT)
        )
        
        price_ladder = validation.price_ladder or [validation.p_ref]
        
        # Calculate position sizes for each price level
        entry_orders = []
        total_allocation = 0.0
        
        for i, price in enumerate(price_ladder[:self.config.ENTRY_LADDER_COUNT]):
            # Allocate budget across ladder (more to realistic price)
            if i == 1:  # Realistic price
                allocation = budget * 0.5
            elif i == 0:  # Optimistic
                allocation = budget * 0.25
            else:  # Pessimistic
                allocation = budget * 0.25
            
            amount = allocation / price if price > 0 else 0
            total_allocation += allocation
            
            entry_orders.append({
                'price': price,
                'amount': amount,
                'allocation_usdt': allocation,
                'order_type': 'limit',
                'side': 'buy'
            })
        
        # Exit plan
        exit_plan = {
            'take_profit_levels': [
                {'price_multiplier': 1.0 + tp, 'allocation': 0.33}
                for tp in self.config.TAKE_PROFIT_STEPS
            ],
            'stop_loss_pct': self.config.STOP_LOSS_PCT,
            'max_time_seconds': self.config.EXIT_TIME_SECONDS,
            'circuit_breaker_spread_pct': self.config.CIRCUIT_BREAKER_SPREAD_PCT
        }
        
        return {
            'symbol': event.trading_pair,
            'budget_usdt': budget,
            'entry_orders': entry_orders,
            'exit_plan': exit_plan,
            'listing_time': event.listing_time.isoformat()
        }
    
    async def close(self):
        """Close exchange connection."""
        if self.exchange:
            await self.exchange.close()
            self.exchange = None

