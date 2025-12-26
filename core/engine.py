"""
DEPRECATED: This file is kept for backward compatibility.

The TradingEngine has been moved to modules/conservative/execution/engine.py

This file will be removed in a future version.
Please update imports to use:
    from modules.conservative.execution.engine import TradingEngine
"""

# Re-export for backward compatibility
from modules.conservative.execution.engine import TradingEngine

__all__ = ['TradingEngine']
