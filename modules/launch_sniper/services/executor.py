"""
Phase E: Execution - Execute trades using FSM.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import ccxt.async_support as ccxt

from modules.launch_sniper.core.fsm import ExecutionFSM, ExecutionState
from modules.launch_sniper.core.events import ExecutionEvent
from modules.launch_sniper.services.validator import ValidationService
from modules.launch_sniper.config import LaunchSniperConfig

logger = logging.getLogger(__name__)


class ExecutionService:
    """Execution service for launch sniper."""
    
    def __init__(self):
        self.config = LaunchSniperConfig
        self.exchange: Optional[ccxt.bybit] = None
        self.validator = ValidationService()
    
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
            logger.info("Execution service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize execution service: {e}")
            raise
    
    async def execute_trade_plan(
        self,
        fsm: ExecutionFSM,
        trade_plan: Dict[str, Any]
    ) -> List[ExecutionEvent]:
        """
        Execute trade plan using FSM.
        
        IMPORTANT: No AI calls during execution.
        Only deterministic logic based on trade plan.
        
        Args:
            fsm: Execution FSM
            trade_plan: Static trade plan from arming phase
            
        Returns:
            List of execution events
        """
        events = []
        
        if not self.exchange:
            await self.initialize()
        
        try:
            # Wait for listing time
            await self._wait_for_listing(fsm)
            if fsm.is_terminal():
                return events
            
            # Enter position
            entry_result = await self._enter_position(fsm, trade_plan)
            events.extend(entry_result.get('events', []))
            
            if fsm.is_terminal():
                return events
            
            # Manage position and exit
            exit_result = await self._manage_and_exit(fsm, trade_plan)
            events.extend(exit_result.get('events', []))
            
        except Exception as e:
            logger.error(f"Execution error: {e}")
            fsm.transition_to(ExecutionState.ABORT, f"Execution error: {e}")
            events.append(ExecutionEvent(
                event_id=fsm.ctx.event_id,
                phase="EXECUTION",
                state=ExecutionState.ABORT.value,
                action_taken="ABORT",
                execution_result=f"Error: {e}"
            ))
        
        return events
    
    async def _wait_for_listing(self, fsm: ExecutionFSM):
        """Wait until listing time."""
        while datetime.utcnow() < fsm.ctx.listing_time:
            if fsm.get_state() != ExecutionState.ARMED:
                return
            
            await asyncio.sleep(1)  # Check every second
        
        # Listing time reached
        fsm.transition_to(ExecutionState.ENTERING, "Listing time reached")
    
    async def _enter_position(
        self,
        fsm: ExecutionFSM,
        trade_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enter position using ladder orders."""
        result = {'events': [], 'orders': []}
        
        entry_orders = trade_plan.get('entry_orders', [])
        symbol = trade_plan.get('symbol', '')
        
        # Place all entry orders
        placed_orders = []
        for order_spec in entry_orders:
            try:
                if self.config.DRY_RUN:
                    # Simulate order placement
                    order = {
                        'id': f"dry_run_{len(placed_orders)}",
                        'symbol': symbol,
                        'type': order_spec['order_type'],
                        'side': order_spec['side'],
                        'price': order_spec['price'],
                        'amount': order_spec['amount'],
                        'status': 'open'
                    }
                else:
                    order = await self.exchange.create_limit_order(
                        symbol=symbol,
                        side=order_spec['side'],
                        amount=order_spec['amount'],
                        price=order_spec['price']
                    )
                
                placed_orders.append(order)
                result['orders'].append(order)
                
                events.append(ExecutionEvent(
                    event_id=fsm.ctx.event_id,
                    phase="ENTERING",
                    state=ExecutionState.ENTERING.value,
                    action_taken=f"PLACE_ORDER",
                    execution_result=f"Order placed: {order.get('id', 'unknown')}",
                    metadata={'order': order}
                ))
                
            except Exception as e:
                logger.error(f"Failed to place order: {e}")
                events.append(ExecutionEvent(
                    event_id=fsm.ctx.event_id,
                    phase="ENTERING",
                    state=ExecutionState.ENTERING.value,
                    action_taken="PLACE_ORDER_FAILED",
                    execution_result=f"Error: {e}"
                ))
        
        # Wait for fills (with timeout)
        timeout = datetime.utcnow() + timedelta(seconds=self.config.ENTRY_TIMEOUT_SECONDS)
        filled_amount = 0.0
        filled_value = 0.0
        
        while datetime.utcnow() < timeout:
            # Check order statuses
            for order in placed_orders:
                try:
                    if self.config.DRY_RUN:
                        # Simulate partial fill
                        order['filled'] = order['amount'] * 0.5
                        order['status'] = 'closed'
                    else:
                        order_status = await self.exchange.fetch_order(order['id'], symbol)
                        order['filled'] = order_status.get('filled', 0)
                        order['status'] = order_status.get('status', 'open')
                    
                    if order['status'] == 'closed':
                        filled_amount += order['filled']
                        filled_value += order['filled'] * order['price']
                
                except Exception as e:
                    logger.debug(f"Error checking order {order.get('id')}: {e}")
            
            if filled_amount > 0:
                break
            
            await asyncio.sleep(0.5)  # Check every 500ms
        
        # Cancel unfilled orders
        for order in placed_orders:
            if order.get('status') != 'closed':
                try:
                    if not self.config.DRY_RUN:
                        await self.exchange.cancel_order(order['id'], symbol)
                    events.append(ExecutionEvent(
                        event_id=fsm.ctx.event_id,
                        phase="ENTERING",
                        state=ExecutionState.ENTERING.value,
                        action_taken="CANCEL_ORDER",
                        execution_result=f"Order cancelled: {order.get('id')}"
                    ))
                except Exception as e:
                    logger.error(f"Failed to cancel order: {e}")
        
        # Update FSM context
        if filled_amount > 0:
            fsm.ctx.position_size = filled_amount
            fsm.ctx.entry_price = filled_value / filled_amount if filled_amount > 0 else 0
            fsm.transition_to(ExecutionState.IN_POSITION, f"Position entered: {filled_amount}")
        else:
            fsm.transition_to(ExecutionState.ABORT, "No fills within timeout")
        
        result['events'] = events
        result['filled_amount'] = filled_amount
        result['entry_price'] = fsm.ctx.entry_price
        
        return result
    
    async def _manage_and_exit(
        self,
        fsm: ExecutionFSM,
        trade_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Manage position and exit."""
        result = {'events': [], 'exit_reason': None}
        
        if fsm.ctx.position_size == 0:
            fsm.transition_to(ExecutionState.ABORT, "No position to exit")
            return result
        
        exit_plan = trade_plan.get('exit_plan', {})
        symbol = trade_plan.get('symbol', '')
        entry_price = fsm.ctx.entry_price
        
        # Calculate exit prices
        tp_levels = exit_plan.get('take_profit_levels', [])
        stop_loss_price = entry_price * (1 - exit_plan.get('stop_loss_pct', 0.1))
        max_time = datetime.utcnow() + timedelta(seconds=exit_plan.get('max_time_seconds', 120))
        
        # Place TP orders
        tp_orders = []
        for tp_level in tp_levels:
            tp_price = entry_price * tp_level['price_multiplier']
            tp_amount = fsm.ctx.position_size * tp_level['allocation']
            
            try:
                if self.config.DRY_RUN:
                    order = {'id': f"tp_{len(tp_orders)}", 'status': 'open'}
                else:
                    order = await self.exchange.create_limit_order(
                        symbol=symbol,
                        side='sell',
                        amount=tp_amount,
                        price=tp_price
                    )
                
                tp_orders.append(order)
                
            except Exception as e:
                logger.error(f"Failed to place TP order: {e}")
        
        # Monitor and exit
        position_start = datetime.utcnow()
        initial_liquidity = 1000.0  # Placeholder - should be measured
        
        while datetime.utcnow() < max_time:
            if fsm.get_state() != ExecutionState.IN_POSITION:
                break
            
            # Check current price
            try:
                ticker = await self.exchange.fetch_ticker(symbol)
                current_price = ticker.get('last', entry_price)
                spread = (ticker.get('ask', 0) - ticker.get('bid', 0)) / current_price if current_price > 0 else 0
                
                # Check circuit breaker
                should_abort, reason = self.validator.check_circuit_breaker(
                    spread * 100,  # Convert to percentage
                    initial_liquidity,
                    initial_liquidity * 0.8  # Placeholder
                )
                
                if should_abort:
                    fsm.transition_to(ExecutionState.EXITING, f"Circuit breaker: {reason}")
                    result['exit_reason'] = reason
                    break
                
                # Check stop loss
                if current_price <= stop_loss_price:
                    fsm.transition_to(ExecutionState.EXITING, "Stop loss hit")
                    result['exit_reason'] = "STOP_LOSS"
                    break
                
            except Exception as e:
                logger.debug(f"Error checking price: {e}")
            
            await asyncio.sleep(0.5)
        
        # Time-based exit
        if fsm.get_state() == ExecutionState.IN_POSITION:
            fsm.transition_to(ExecutionState.EXITING, "Time-based exit")
            result['exit_reason'] = "TIME"
        
        # Execute exit
        if fsm.get_state() == ExecutionState.EXITING:
            exit_result = await self._execute_exit(fsm, symbol, result['exit_reason'])
            result['events'].extend(exit_result.get('events', []))
            result['exit_price'] = exit_result.get('exit_price', 0)
        
        return result
    
    async def _execute_exit(
        self,
        fsm: ExecutionFSM,
        symbol: str,
        exit_reason: str
    ) -> Dict[str, Any]:
        """Execute exit from position."""
        result = {'events': [], 'exit_price': 0}
        
        # Cancel remaining TP orders
        # Then market sell remaining position
        
        try:
            if self.config.DRY_RUN:
                # Simulate exit
                ticker = {'last': fsm.ctx.entry_price * 1.05}  # 5% profit simulation
                exit_price = ticker['last']
            else:
                ticker = await self.exchange.fetch_ticker(symbol)
                exit_price = ticker.get('last', fsm.ctx.entry_price)
                
                # Market sell remaining position
                await self.exchange.create_market_order(
                    symbol=symbol,
                    side='sell',
                    amount=fsm.ctx.position_size
                )
            
            fsm.ctx.exit_price = exit_price
            fsm.ctx.pnl_usdt = (exit_price - fsm.ctx.entry_price) * fsm.ctx.position_size
            fsm.ctx.pnl_percent = ((exit_price - fsm.ctx.entry_price) / fsm.ctx.entry_price) * 100
            
            fsm.transition_to(ExecutionState.DONE, f"Exit completed: {exit_reason}")
            
            result['exit_price'] = exit_price
            result['events'].append(ExecutionEvent(
                event_id=fsm.ctx.event_id,
                phase="EXITING",
                state=ExecutionState.DONE.value,
                action_taken="EXIT",
                execution_result=f"Exited at {exit_price}, PnL: {fsm.ctx.pnl_percent:.2f}%",
                metadata={'exit_reason': exit_reason}
            ))
            
        except Exception as e:
            logger.error(f"Exit error: {e}")
            fsm.transition_to(ExecutionState.ABORT, f"Exit failed: {e}")
            result['events'].append(ExecutionEvent(
                event_id=fsm.ctx.event_id,
                phase="EXITING",
                state=ExecutionState.ABORT.value,
                action_taken="EXIT_FAILED",
                execution_result=f"Error: {e}"
            ))
        
        return result
    
    async def close(self):
        """Close exchange connection."""
        if self.exchange:
            await self.exchange.close()
            self.exchange = None

