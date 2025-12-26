"""
Event definitions for launch sniper.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4


@dataclass
class LaunchEvent:
    """Launch event discovered from Bybit."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    symbol: str = ""
    trading_pair: str = ""
    listing_time: datetime = field(default_factory=datetime.utcnow)
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    source: str = "bybit"  # bybit, manual, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'event_id': self.event_id,
            'symbol': self.symbol,
            'trading_pair': self.trading_pair,
            'listing_time': self.listing_time.isoformat(),
            'discovered_at': self.discovered_at.isoformat(),
            'source': self.source,
            'metadata': self.metadata
        }


@dataclass
class AIDecision:
    """AI decision for launch event."""
    event_id: str
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    classification: str = ""  # HYPE, NEUTRAL, SUSPICIOUS
    confidence: float = 0.0
    reasoning: str = ""
    claims: List[str] = field(default_factory=list)  # Parsed claims from AI
    risk_flags: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    raw_response: Optional[str] = None
    parsed_response: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'event_id': self.event_id,
            'decision_id': self.decision_id,
            'classification': self.classification,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'claims': self.claims,
            'risk_flags': self.risk_flags,
            'timestamp': self.timestamp.isoformat(),
            'raw_response': self.raw_response,
            'parsed_response': self.parsed_response
        }


@dataclass
class ValidationResult:
    """Result of deterministic validation."""
    event_id: str
    validation_id: str = field(default_factory=lambda: str(uuid4()))
    decision: str = ""  # GO, ABORT_REASON_*
    p_ref: float = 0.0  # Reference price
    price_ladder: List[float] = field(default_factory=list)  # Optimistic, realistic, pessimistic
    validated_facts: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'event_id': self.event_id,
            'validation_id': self.validation_id,
            'decision': self.decision,
            'p_ref': self.p_ref,
            'price_ladder': self.price_ladder,
            'validated_facts': self.validated_facts,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ExecutionEvent:
    """Execution event for logging."""
    event_id: str
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    phase: str = ""  # ARMED, ENTERING, IN_POSITION, EXITING, DONE, ABORT
    state: str = ""
    action_taken: str = ""
    execution_result: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'event_id': self.event_id,
            'execution_id': self.execution_id,
            'phase': self.phase,
            'state': self.state,
            'action_taken': self.action_taken,
            'execution_result': self.execution_result,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class TradeResult:
    """Final trade result."""
    event_id: str
    trade_id: str = field(default_factory=lambda: str(uuid4()))
    symbol: str = ""
    entry_price: float = 0.0
    exit_price: float = 0.0
    position_size: float = 0.0
    pnl_usdt: float = 0.0
    pnl_percent: float = 0.0
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    exit_reason: str = ""  # TP, SL, TIME, CIRCUIT_BREAKER
    execution_events: List[ExecutionEvent] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'event_id': self.event_id,
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'position_size': self.position_size,
            'pnl_usdt': self.pnl_usdt,
            'pnl_percent': self.pnl_percent,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_reason': self.exit_reason,
            'execution_events_count': len(self.execution_events),
            'timestamp': self.timestamp.isoformat()
        }

