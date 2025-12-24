"""
Event-Driven architecture for trading bot.
Provides EventBus and event types for decoupled component communication.
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Awaitable
from enum import Enum
from loguru import logger
import asyncio


class EventType(Enum):
    """Event types for classification."""
    MARKET_DATA = "market_data"
    SIGNAL = "signal"
    ORDER = "order"
    POSITION = "position"
    ERROR = "error"
    SYSTEM = "system"


@dataclass
class Event(ABC):
    """Base event class."""
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'metadata': self.metadata
        }


@dataclass
class MarketDataEvent(Event):
    """Event for market data updates."""
    symbol: str = ""
    price: float = 0.0
    volume: float = 0.0
    indicators: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        self.event_type = EventType.MARKET_DATA
        if not hasattr(self, 'metadata') or self.metadata is None:
            self.metadata = {}
        self.metadata.update({
            'symbol': self.symbol,
            'price': self.price,
            'volume': self.volume,
            'indicators': self.indicators
        })


@dataclass
class SignalEvent(Event):
    """Event for trading signals."""
    symbol: str = ""
    action: str = "HOLD"  # BUY, SELL, HOLD
    confidence: float = 0.0
    reasoning: str = ""
    indicators: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        self.event_type = EventType.SIGNAL
        if not hasattr(self, 'metadata') or self.metadata is None:
            self.metadata = {}
        self.metadata.update({
            'symbol': self.symbol,
            'action': self.action,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'indicators': self.indicators
        })


@dataclass
class OrderEvent(Event):
    """Event for order lifecycle."""
    order_id: str = ""
    symbol: str = ""
    side: str = "buy"  # buy, sell
    state: str = "pending"  # pending, submitted, filled, etc.
    amount: float = 0.0
    filled_amount: float = 0.0
    
    def __post_init__(self):
        self.event_type = EventType.ORDER
        if not hasattr(self, 'metadata') or self.metadata is None:
            self.metadata = {}
        self.metadata.update({
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side,
            'state': self.state,
            'amount': self.amount,
            'filled_amount': self.filled_amount
        })


@dataclass
class PositionEvent(Event):
    """Event for position changes."""
    symbol: str = ""
    action: str = "opened"  # opened, closed
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    
    def __post_init__(self):
        self.event_type = EventType.POSITION
        if not hasattr(self, 'metadata') or self.metadata is None:
            self.metadata = {}
        self.metadata.update({
            'symbol': self.symbol,
            'action': self.action,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'pnl': self.pnl
        })


@dataclass
class ErrorEvent(Event):
    """Event for errors."""
    error_code: str
    error_message: str
    component: str
    severity: str
    
    def __post_init__(self):
        self.event_type = EventType.ERROR
        self.metadata.update({
            'error_code': self.error_code,
            'error_message': self.error_message,
            'component': self.component,
            'severity': self.severity
        })


class EventBus:
    """
    Event bus for pub/sub pattern.
    
    Allows components to emit events and subscribe to event types.
    """
    
    def __init__(self):
        """Initialize event bus."""
        self.subscribers: Dict[EventType, List[Callable[[Event], Awaitable[None]]]] = {}
        self.event_history: List[Event] = []
        self.max_history = 1000
        self.stats = {
            'total_events': 0,
            'by_type': {},
            'errors': 0
        }
    
    def subscribe(
        self, 
        event_type: EventType, 
        handler: Callable[[Event], Awaitable[None]]
    ) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Async function to handle the event
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type.value} events")
    
    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Awaitable[None]]
    ) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        if event_type in self.subscribers:
            if handler in self.subscribers[event_type]:
                self.subscribers[event_type].remove(handler)
                logger.debug(f"Unsubscribed from {event_type.value} events")
    
    async def emit(self, event: Event) -> None:
        """
        Emit an event to all subscribers.
        
        Args:
            event: Event to emit
        """
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
        
        # Update statistics
        self.stats['total_events'] += 1
        event_type_str = event.event_type.value
        self.stats['by_type'][event_type_str] = self.stats['by_type'].get(event_type_str, 0) + 1
        
        if event.event_type == EventType.ERROR:
            self.stats['errors'] += 1
        
        # Get subscribers for this event type
        handlers = self.subscribers.get(event.event_type, [])
        
        if not handlers:
            logger.debug(f"No subscribers for {event.event_type.value} event")
            return
        
        # Call all handlers
        logger.debug(f"Emitting {event.event_type.value} event to {len(handlers)} subscribers")
        
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    f"Error in event handler for {event.event_type.value}: {e}",
                    exc_info=True
                )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            'total_events': self.stats['total_events'],
            'by_type': self.stats['by_type'],
            'errors': self.stats['errors'],
            'subscribers': {
                event_type.value: len(handlers)
                for event_type, handlers in self.subscribers.items()
            },
            'recent_events': [
                e.to_dict() for e in self.event_history[-10:]
            ]
        }
    
    def clear_history(self):
        """Clear event history."""
        self.event_history.clear()
        logger.info("Event history cleared")


# Global event bus instance
event_bus = EventBus()

