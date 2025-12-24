"""Validation and safety checks for production readiness."""

from typing import Dict, Any, List
from loguru import logger
from config import settings


class SafetyValidator:
    """Validates configuration and prevents dangerous operations."""

    @staticmethod
    def validate_configuration() -> Dict[str, Any]:
        """
        Validate all configuration settings for safety.
        
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Check dry run mode
        if not settings.dry_run:
            warnings.append(
                "DRY_RUN is False - Real trading is enabled! "
                "Ensure you've tested thoroughly in dry-run mode first."
            )
        
        # Check API keys
        if not settings.bybit_api_key or settings.bybit_api_key == "your_bybit_api_key_here":
            issues.append("BYBIT_API_KEY is not set or is placeholder")
        
        if not settings.bybit_api_secret or settings.bybit_api_secret == "your_bybit_api_secret_here":
            issues.append("BYBIT_API_SECRET is not set or is placeholder")
        
        if not settings.grok_api_key or settings.grok_api_key == "your_grok_api_key_here":
            issues.append("GROK_API_KEY is not set or is placeholder")
        
        # Check risk parameters
        if settings.stop_loss_pct > 5.0:
            warnings.append(
                f"Stop-loss is {settings.stop_loss_pct}% - "
                "Consider using a tighter stop-loss (2-3%) for better risk management"
            )
        
        if settings.stop_loss_pct < 1.0:
            warnings.append(
                f"Stop-loss is {settings.stop_loss_pct}% - "
                "Very tight stop-loss may result in premature exits"
            )
        
        if settings.trading_balance < 10.0:
            warnings.append(
                f"Trading balance is ${settings.trading_balance} - "
                "Very small balance may limit trading opportunities"
            )
        
        if settings.min_ai_confidence < 70.0:
            warnings.append(
                f"Minimum AI confidence is {settings.min_ai_confidence}% - "
                "Consider using higher threshold (80%+) for better trade quality"
            )
        
        # Check testnet
        if not settings.bybit_testnet and not settings.dry_run:
            warnings.append(
                "BYBIT_TESTNET is False and DRY_RUN is False - "
                "You are trading on mainnet with real money!"
            )
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }

    @staticmethod
    def validate_trade_safety(
        symbol: str,
        entry_price: float,
        position_size: float,
        balance: float
    ) -> Dict[str, Any]:
        """
        Validate trade safety before execution.
        
        Args:
            symbol: Trading pair symbol
            entry_price: Entry price
            position_size: Position size
            balance: Available balance
            
        Returns:
            Validation result
        """
        issues = []
        
        # Check position size
        trade_value = entry_price * position_size
        if trade_value > balance * 0.95:  # Leave 5% buffer
            issues.append(
                f"Trade value ${trade_value:.2f} exceeds 95% of balance ${balance:.2f}"
            )
        
        # Check minimum trade size
        if trade_value < 5.0:
            issues.append(
                f"Trade value ${trade_value:.2f} is too small (minimum $5 recommended)"
            )
        
        # Check price validity
        if entry_price <= 0:
            issues.append(f"Invalid entry price: ${entry_price:.2f}")
        
        # Check position size validity
        if position_size <= 0:
            issues.append(f"Invalid position size: {position_size:.6f}")
        
        return {
            'is_safe': len(issues) == 0,
            'issues': issues
        }

    @staticmethod
    def check_production_readiness() -> Dict[str, Any]:
        """
        Comprehensive check for production readiness.
        
        Returns:
            Readiness assessment
        """
        config_validation = SafetyValidator.validate_configuration()
        
        readiness_score = 100
        blockers = []
        recommendations = []
        
        # Check for critical issues
        if config_validation['issues']:
            readiness_score -= 50
            blockers.extend(config_validation['issues'])
        
        # Check dry run
        if not settings.dry_run:
            readiness_score -= 20
            blockers.append("DRY_RUN is False - ensure thorough testing first")
        
        # Check testnet
        if not settings.bybit_testnet and not settings.dry_run:
            readiness_score -= 10
            blockers.append("Trading on mainnet without testnet testing")
        
        # Warnings become recommendations
        recommendations.extend(config_validation['warnings'])
        
        # Additional recommendations
        if settings.min_ai_confidence < 80.0:
            recommendations.append("Consider increasing MIN_AI_CONFIDENCE to 80%+")
        
        if settings.stop_loss_pct > 3.0:
            recommendations.append("Consider tightening stop-loss to 2-3%")
        
        status = "READY" if readiness_score >= 80 and not blockers else "NOT READY"
        
        return {
            'status': status,
            'score': readiness_score,
            'blockers': blockers,
            'recommendations': recommendations,
            'config_validation': config_validation
        }

