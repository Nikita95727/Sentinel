"""
Finite State Machine for launch sniper execution.
"""
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


class ExecutionState(Enum):
    """Execution states for launch sniper."""
    WAIT_LISTING = "WAIT_LISTING"  # Waiting for listing time
    ARMED = "ARMED"  # Ready, waiting for listing start
    ENTERING = "ENTERING"  # Placing entry orders
    IN_POSITION = "IN_POSITION"  # Position opened, managing exit
    EXITING = "EXITING"  # Closing position
    DONE = "DONE"  # Successfully completed
    ABORT = "ABORT"  # Aborted due to error or circuit breaker


@dataclass
class ExecutionContext:
    """Context for FSM execution."""
    event_id: str
    symbol: str
    listing_time: datetime
    state: ExecutionState
    state_entered_at: Optional[datetime] = None
    entry_orders: list = None
    exit_orders: list = None
    position_size: float = 0.0
    entry_price: float = 0.0
    exit_price: float = 0.0
    pnl_usdt: float = 0.0
    pnl_percent: float = 0.0
    abort_reason: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.entry_orders is None:
            self.entry_orders = []
        if self.exit_orders is None:
            self.exit_orders = []
        if self.metadata is None:
            self.metadata = {}


class ExecutionFSM:
    """Finite State Machine for launch sniper execution."""
    
    def __init__(self, event_id: str, symbol: str, listing_time: datetime):
        self.ctx = ExecutionContext(
            event_id=event_id,
            symbol=symbol,
            listing_time=listing_time,
            state=ExecutionState.WAIT_LISTING
        )
        self.ctx.state_entered_at = datetime.utcnow()
    
    def transition_to(self, new_state: ExecutionState, reason: Optional[str] = None):
        """Transition to new state."""
        old_state = self.ctx.state
        self.ctx.state = new_state
        self.ctx.state_entered_at = datetime.utcnow()
        
        if reason and new_state == ExecutionState.ABORT:
            self.ctx.abort_reason = reason
        
        return {
            'old_state': old_state.value,
            'new_state': new_state.value,
            'timestamp': self.ctx.state_entered_at.isoformat(),
            'reason': reason
        }
    
    def get_state(self) -> ExecutionState:
        """Get current state."""
        return self.ctx.state
    
    def get_context(self) -> ExecutionContext:
        """Get execution context."""
        return self.ctx
    
    def is_terminal(self) -> bool:
        """Check if in terminal state."""
        return self.ctx.state in (ExecutionState.DONE, ExecutionState.ABORT)
    
    def can_transition(self, target_state: ExecutionState) -> bool:
        """Check if transition is allowed."""
        current = self.ctx.state
        
        # Define allowed transitions
        transitions = {
            ExecutionState.WAIT_LISTING: [ExecutionState.ARMED, ExecutionState.ABORT],
            ExecutionState.ARMED: [ExecutionState.ENTERING, ExecutionState.ABORT],
            ExecutionState.ENTERING: [ExecutionState.IN_POSITION, ExecutionState.ABORT],
            ExecutionState.IN_POSITION: [ExecutionState.EXITING, ExecutionState.ABORT],
            ExecutionState.EXITING: [ExecutionState.DONE, ExecutionState.ABORT],
            ExecutionState.DONE: [],
            ExecutionState.ABORT: []
        }
        
        return target_state in transitions.get(current, [])

