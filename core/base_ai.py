"""Base abstract class for AI providers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4


class AIDecision:
    """AI trading decision with structured data."""
    
    def __init__(
        self,
        action: str,
        confidence: float,
        reasoning: str,
        risk_level: str = "medium",
        additional_context: Optional[Dict[str, Any]] = None,
        decision_id: Optional[str] = None
    ):
        """
        Initialize AI decision.
        
        Args:
            action: Trading action ('BUY', 'SELL', 'HOLD', 'ABSTAIN')
            confidence: Confidence score (0-100)
            reasoning: Explanation for the decision
            risk_level: Risk assessment ('low', 'medium', 'high')
            additional_context: Any additional context data
            decision_id: Unique decision ID (UUID). If None, generates new UUID.
        """
        self.decision_id = decision_id if decision_id else str(uuid4())
        self.action = action.upper()
        self.confidence = confidence
        self.reasoning = reasoning
        self.risk_level = risk_level
        self.additional_context = additional_context or {}
        self.timestamp = datetime.utcnow()

    def should_execute(self, min_confidence: float = 80.0) -> bool:
        """
        Check if decision should be executed based on confidence threshold.
        
        Args:
            min_confidence: Minimum confidence required
            
        Returns:
            True if confidence >= min_confidence and action is BUY
        """
        return self.action == "BUY" and self.confidence >= min_confidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary."""
        return {
            "decision_id": self.decision_id,
            "action": self.action,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "risk_level": self.risk_level,
            "additional_context": self.additional_context,
            "timestamp": self.timestamp.isoformat()
        }


class BaseAI(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def analyze(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        technical_indicators: Dict[str, float],
        memory: Optional[List[Dict[str, Any]]] = None
    ) -> AIDecision:
        """
        Analyze market conditions and make a trading decision.
        
        Args:
            symbol: Trading pair symbol
            market_data: Current market data (price, volume, etc.)
            technical_indicators: Calculated indicators (RSI, EMA, ATR, etc.)
            memory: Recent trade history for feedback loop
            
        Returns:
            AIDecision object with action, confidence, and reasoning
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the AI model.
        
        Returns:
            System prompt defining trading behavior
        """
        pass
