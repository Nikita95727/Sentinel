"""
Phase B: AI Context Analysis - Grok analyzes launch event context.
"""
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from modules.launch_sniper.core.events import LaunchEvent, AIDecision
from modules.launch_sniper.config import LaunchSniperConfig

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI analyzer for launch events."""
    
    def __init__(self):
        self.config = LaunchSniperConfig
        self.grok_client = None  # Will be initialized if AI enabled
    
    async def initialize(self):
        """Initialize AI client."""
        if not self.config.AI_ENABLED:
            logger.info("AI analysis disabled")
            return
        
        if not self.config.GROK_API_KEY:
            logger.warning("Grok API key not set, AI analysis disabled")
            return
        
        try:
            # Import Grok provider from main bot
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            
            from providers.grok import GrokProvider
            self.grok_client = GrokProvider(api_key=self.config.GROK_API_KEY)
            logger.info("AI analyzer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AI analyzer: {e}")
            self.grok_client = None
    
    async def analyze_launch_event(
        self,
        event: LaunchEvent,
        market_data: Optional[Dict[str, Any]] = None
    ) -> AIDecision:
        """
        Analyze launch event using AI.
        
        IMPORTANT: AI only provides context and classification.
        AI does NOT make trading decisions.
        
        Args:
            event: Launch event to analyze
            market_data: Additional market data (CMC, etc.)
            
        Returns:
            AIDecision with classification and reasoning
        """
        if not self.grok_client:
            # Return neutral decision if AI not available
            return AIDecision(
                event_id=event.event_id,
                classification="NEUTRAL",
                confidence=0.0,
                reasoning="AI analysis not available",
                claims=[]
            )
        
        try:
            # Build prompt for AI
            prompt = self._build_analysis_prompt(event, market_data)
            
            # Call Grok (using similar interface as main bot)
            # Note: This is a simplified call - adjust based on actual GrokProvider interface
            response = await self._call_grok(prompt)
            
            # Parse response
            decision = self._parse_ai_response(event.event_id, response)
            
            logger.info(f"AI analysis for {event.symbol}: {decision.classification} (confidence: {decision.confidence})")
            return decision
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return AIDecision(
                event_id=event.event_id,
                classification="NEUTRAL",
                confidence=0.0,
                reasoning=f"AI analysis failed: {e}",
                claims=[]
            )
    
    def _build_analysis_prompt(
        self,
        event: LaunchEvent,
        market_data: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for AI analysis."""
        prompt = f"""Analyze this new token listing event for context and classification.

TOKEN INFORMATION:
- Symbol: {event.symbol}
- Trading Pair: {event.trading_pair}
- Listing Time: {event.listing_time.isoformat()}
- Source: {event.source}

ADDITIONAL DATA:
{json.dumps(market_data, indent=2) if market_data else "No additional data available"}

TASK:
1. Classify the event: HYPE, NEUTRAL, or SUSPICIOUS
2. Provide reasoning for classification
3. List risk flags if any
4. Extract factual claims (NOT price predictions)

IMPORTANT:
- Do NOT predict prices
- Do NOT suggest entry/exit points
- Only provide context and classification
- Focus on factual information

Return JSON format:
{{
    "classification": "HYPE|NEUTRAL|SUSPICIOUS",
    "confidence": 0.0-1.0,
    "reasoning": "...",
    "risk_flags": ["..."],
    "claims": ["factual claim 1", "factual claim 2"]
}}
"""
        return prompt
    
    async def _call_grok(self, prompt: str) -> Dict[str, Any]:
        """Call Grok API."""
        # This is a placeholder - adjust based on actual GrokProvider interface
        # The main bot's GrokProvider should be used here
        if hasattr(self.grok_client, 'analyze'):
            # Simplified call - adjust parameters as needed
            result = await self.grok_client.analyze(
                symbol="NEW_LISTING",
                market_data={"prompt": prompt},
                technical_indicators={},
                has_position=False,
                action_space=["BUY", "ABSTAIN"]
            )
            return result.additional_context.get('parsed_response', {})
        else:
            # Fallback if interface differs
            raise NotImplementedError("GrokProvider interface not compatible")
    
    def _parse_ai_response(self, event_id: str, response: Dict[str, Any]) -> AIDecision:
        """Parse AI response into AIDecision."""
        try:
            # Handle both dict and string responses
            if isinstance(response, str):
                response = json.loads(response)
            
            decision = AIDecision(
                event_id=event_id,
                classification=response.get('classification', 'NEUTRAL').upper(),
                confidence=float(response.get('confidence', 0.0)),
                reasoning=response.get('reasoning', ''),
                claims=response.get('claims', []),
                risk_flags=response.get('risk_flags', []),
                raw_response=json.dumps(response) if isinstance(response, dict) else response,
                parsed_response=response if isinstance(response, dict) else None
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return AIDecision(
                event_id=event_id,
                classification="NEUTRAL",
                confidence=0.0,
                reasoning=f"Failed to parse AI response: {e}",
                claims=[]
            )

