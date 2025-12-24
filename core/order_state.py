"""
Order State Machine for tracking order lifecycle.
Handles states: pending, submitted, partial_filled, filled, cancelling, cancelled, rejected, expired.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger


class OrderState(Enum):
    """Order lifecycle states."""
    PENDING = "pending"          # Created locally, not submitted
    SUBMITTED = "submitted"       # Submitted to exchange
    PARTIAL_FILLED = "partial"    # Partially filled
    FILLED = "filled"             # Fully filled
    CANCELLING = "cancelling"     # In process of cancellation
    CANCELLED = "cancelled"       # Cancelled
    REJECTED = "rejected"         # Rejected by exchange
    EXPIRED = "expired"           # Expired


@dataclass
class Order:
    """
    Order model with state machine.
    
    Tracks order lifecycle from creation to completion.
    """
    id: Optional[str]
    symbol: str
    side: str  # buy/sell
    amount: float
    price: Optional[float]
    state: OrderState
    filled_amount: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    exchange_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def can_transition_to(self, new_state: OrderState) -> bool:
        """
        Check if transition to new state is valid.
        
        Args:
            new_state: Target state
            
        Returns:
            True if transition is allowed
        """
        transitions = {
            OrderState.PENDING: [OrderState.SUBMITTED, OrderState.REJECTED],
            OrderState.SUBMITTED: [
                OrderState.PARTIAL_FILLED,
                OrderState.FILLED,
                OrderState.CANCELLING,
                OrderState.REJECTED,
                OrderState.EXPIRED
            ],
            OrderState.PARTIAL_FILLED: [
                OrderState.FILLED,
                OrderState.CANCELLING,
                OrderState.EXPIRED
            ],
            OrderState.CANCELLING: [OrderState.CANCELLED],
            # Terminal states cannot transition
            OrderState.FILLED: [],
            OrderState.CANCELLED: [],
            OrderState.REJECTED: [],
            OrderState.EXPIRED: [],
        }
        
        allowed = new_state in transitions.get(self.state, [])
        if not allowed:
            logger.warning(
                f"Invalid transition from {self.state.value} to {new_state.value} "
                f"for order {self.id}"
            )
        return allowed
    
    def transition_to(self, new_state: OrderState, error: Optional[str] = None):
        """
        Transition to new state.
        
        Args:
            new_state: Target state
            error: Optional error message
        """
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid transition from {self.state.value} to {new_state.value}"
            )
        
        old_state = self.state
        self.state = new_state
        self.updated_at = datetime.now()
        
        if error:
            self.error = error
        
        logger.debug(
            f"Order {self.id} transitioned: {old_state.value} -> {new_state.value}"
        )
    
    def update_filled(self, filled_amount: float):
        """
        Update filled amount and auto-transition if needed.
        
        Args:
            filled_amount: New filled amount
        """
        self.filled_amount = filled_amount
        self.updated_at = datetime.now()
        
        if self.filled_amount >= self.amount:
            self.transition_to(OrderState.FILLED)
        elif self.filled_amount > 0:
            if self.state == OrderState.SUBMITTED:
                self.transition_to(OrderState.PARTIAL_FILLED)
    
    def is_terminal(self) -> bool:
        """Check if order is in terminal state."""
        return self.state in [
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
            OrderState.EXPIRED
        ]
    
    def is_active(self) -> bool:
        """Check if order is active (can be monitored)."""
        return self.state in [
            OrderState.SUBMITTED,
            OrderState.PARTIAL_FILLED
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'amount': self.amount,
            'price': self.price,
            'state': self.state.value,
            'filled_amount': self.filled_amount,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'exchange_id': self.exchange_id,
            'error': self.error,
            'metadata': self.metadata
        }

