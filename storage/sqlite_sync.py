"""
SQLite synchronization for research data.
Duplicates all JSONL data to SQLite database for efficient querying and analysis.
Fully compatible with JSONL structure.
"""

import sqlite3
import json
import aiofiles
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from loguru import logger
import asyncio


class SQLiteSync:
    """
    Synchronizes JSONL files to SQLite database.
    Maintains full compatibility with JSONL structure.
    """
    
    def __init__(self, db_path: str = "storage/research.db", trades_dir: str = "storage/trades", analytics_dir: str = "storage/analytics"):
        """
        Initialize SQLite sync.
        
        Args:
            db_path: Path to SQLite database
            trades_dir: Directory with trade JSONL files
            analytics_dir: Directory with analytics JSONL files
        """
        self.db_path = Path(db_path)
        self.trades_dir = Path(trades_dir)
        self.analytics_dir = Path(analytics_dir)
        
        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table (compatible with JSONL structure)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY,
                decision_id TEXT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                status TEXT NOT NULL,
                outcome TEXT,
                entry_price REAL,
                exit_price REAL,
                position_size REAL,
                entry_time TEXT,
                exit_time TEXT,
                entry_reason TEXT,
                exit_reason TEXT,
                ai_confidence REAL,
                stop_loss REAL,
                take_profit REAL,
                pnl_usdt REAL,
                pnl_percent REAL,
                mfe_percent REAL,
                mae_percent REAL,
                holding_time_hours REAL,
                -- Full JSON data for compatibility
                full_data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # AI Decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT UNIQUE,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT,
                confidence REAL,
                reasoning TEXT,
                risk_level TEXT,
                executed BOOLEAN DEFAULT 0,
                -- Structured fields
                thesis TEXT,
                bull_case TEXT,
                bear_case TEXT,
                risk_flags TEXT,  -- JSON array
                time_horizon TEXT,
                invalid_if TEXT,
                news_refs TEXT,  -- JSON array
                -- Full JSON data
                full_data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Market Conditions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price REAL,
                volume REAL,
                indicators TEXT,  -- JSON object
                full_data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Anomalies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                severity TEXT,
                anomaly_flags TEXT,  -- JSON array
                full_data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Decision Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decision_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT,
                timestamp TEXT NOT NULL,
                executed BOOLEAN,
                trade_result TEXT,  -- JSON object
                full_data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for efficient queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_decision_id ON trades(decision_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_decision_id ON ai_decisions(decision_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_symbol ON ai_decisions(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON ai_decisions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_action ON ai_decisions(action)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conditions_symbol ON market_conditions(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conditions_timestamp ON market_conditions(timestamp)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_symbol ON anomalies(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_timestamp ON anomalies(timestamp)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_decision_id ON decision_results(decision_id)")
        
        conn.commit()
        conn.close()
        logger.info(f"SQLite database initialized at {self.db_path}")
    
    async def sync_trades(self, days_back: Optional[int] = None) -> int:
        """
        Sync trades from JSONL files to SQLite.
        
        Args:
            days_back: Number of days to sync (None = all)
        
        Returns:
            Number of trades synced
        """
        synced_count = 0
        
        # Get all trade files
        trade_files = list(self.trades_dir.glob("trades_*.jsonl"))
        
        if days_back:
            cutoff_date = date.today() - timedelta(days=days_back)
            trade_files = [
                f for f in trade_files
                if self._extract_date_from_filename(f) >= cutoff_date
            ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for file_path in sorted(trade_files):
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    async for line in f:
                        if not line.strip():
                            continue
                        
                        try:
                            trade = json.loads(line.strip())
                            trade_id = trade.get('trade_id')
                            
                            # Check if already synced
                            cursor.execute("SELECT trade_id FROM trades WHERE trade_id = ?", (trade_id,))
                            if cursor.fetchone():
                                continue
                            
                            # Extract key fields
                            entry = trade.get('entry', {})
                            exit_data = trade.get('exit', {})
                            results = trade.get('results', {})
                            
                            cursor.execute("""
                                INSERT OR REPLACE INTO trades (
                                    trade_id, decision_id, symbol, side, status, outcome,
                                    entry_price, exit_price, position_size,
                                    entry_time, exit_time, entry_reason, exit_reason,
                                    ai_confidence, stop_loss, take_profit,
                                    pnl_usdt, pnl_percent, mfe_percent, mae_percent,
                                    holding_time_hours, full_data, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                trade_id,
                                trade.get('decision_id'),
                                trade.get('symbol'),
                                trade.get('side'),
                                trade.get('status'),
                                trade.get('outcome'),
                                entry.get('price'),
                                exit_data.get('price') if exit_data else None,
                                entry.get('position_size'),
                                entry.get('time'),
                                exit_data.get('time') if exit_data else None,
                                entry.get('reason'),
                                exit_data.get('reason') if exit_data else None,
                                entry.get('ai_confidence'),
                                trade.get('risk_management', {}).get('stop_loss'),
                                trade.get('risk_management', {}).get('take_profit'),
                                results.get('pnl_usdt'),
                                results.get('pnl_percent'),
                                results.get('mfe_percent'),
                                results.get('mae_percent'),
                                results.get('holding_time_hours'),
                                json.dumps(trade, ensure_ascii=False),  # Full JSON for compatibility
                                datetime.utcnow().isoformat()
                            ))
                            
                            synced_count += 1
                            
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON in {file_path}: {e}")
                            continue
                
                conn.commit()
                
            except Exception as e:
                logger.error(f"Error syncing trades from {file_path}: {e}")
        
        conn.close()
        logger.info(f"Synced {synced_count} trades to SQLite")
        return synced_count
    
    async def sync_analytics(self, event_type: str, days_back: Optional[int] = None) -> int:
        """
        Sync analytics events from JSONL files to SQLite.
        
        Args:
            event_type: Type of event ('ai_decisions', 'market_conditions', 'anomalies', 'decision_results')
            days_back: Number of days to sync (None = all)
        
        Returns:
            Number of events synced
        """
        synced_count = 0
        
        # Get all files for this event type
        pattern = f"{event_type}_*.jsonl"
        event_files = list(self.analytics_dir.glob(pattern))
        
        if days_back:
            from datetime import timedelta
            cutoff_date = date.today() - timedelta(days=days_back)
            event_files = [
                f for f in event_files
                if self._extract_date_from_filename(f) >= cutoff_date
            ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for file_path in sorted(event_files):
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    async for line in f:
                        if not line.strip():
                            continue
                        
                        try:
                            event = json.loads(line.strip())
                            
                            if event_type == 'ai_decisions':
                                decision_id = event.get('decision_id')
                                if not decision_id:
                                    decision_data = event.get('decision', {})
                                    if isinstance(decision_data, dict):
                                        decision_id = decision_data.get('decision_id')
                                
                                # Check if already synced
                                if decision_id:
                                    cursor.execute("SELECT id FROM ai_decisions WHERE decision_id = ?", (decision_id,))
                                    if cursor.fetchone():
                                        continue
                                
                                decision = event.get('decision', {})
                                additional_context = decision.get('additional_context', {})
                                
                                cursor.execute("""
                                    INSERT OR REPLACE INTO ai_decisions (
                                        decision_id, timestamp, symbol, action, confidence,
                                        reasoning, risk_level, executed,
                                        thesis, bull_case, bear_case, risk_flags,
                                        time_horizon, invalid_if, news_refs, full_data
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    decision_id,
                                    event.get('timestamp'),
                                    event.get('symbol'),
                                    decision.get('action'),
                                    decision.get('confidence'),
                                    decision.get('reasoning'),
                                    decision.get('risk_level'),
                                    1 if event.get('executed') else 0,
                                    additional_context.get('thesis'),
                                    additional_context.get('bull_case'),
                                    additional_context.get('bear_case'),
                                    json.dumps(additional_context.get('risk_flags', []), ensure_ascii=False),
                                    additional_context.get('time_horizon'),
                                    additional_context.get('invalid_if'),
                                    json.dumps(additional_context.get('news_refs', []), ensure_ascii=False),
                                    json.dumps(event, ensure_ascii=False)
                                ))
                                
                            elif event_type == 'market_conditions':
                                cursor.execute("""
                                    INSERT INTO market_conditions (
                                        timestamp, symbol, price, volume, indicators, full_data
                                    ) VALUES (?, ?, ?, ?, ?, ?)
                                """, (
                                    event.get('timestamp'),
                                    event.get('symbol'),
                                    event.get('price'),
                                    event.get('volume'),
                                    json.dumps(event.get('indicators', {}), ensure_ascii=False),
                                    json.dumps(event, ensure_ascii=False)
                                ))
                                
                            elif event_type == 'anomalies':
                                cursor.execute("""
                                    INSERT INTO anomalies (
                                        timestamp, symbol, severity, anomaly_flags, full_data
                                    ) VALUES (?, ?, ?, ?, ?)
                                """, (
                                    event.get('timestamp'),
                                    event.get('symbol'),
                                    event.get('severity'),
                                    json.dumps(event.get('anomaly_flags', []), ensure_ascii=False),
                                    json.dumps(event, ensure_ascii=False)
                                ))
                                
                            elif event_type == 'decision_results':
                                cursor.execute("""
                                    INSERT INTO decision_results (
                                        decision_id, timestamp, executed, trade_result, full_data
                                    ) VALUES (?, ?, ?, ?, ?)
                                """, (
                                    event.get('decision_id'),
                                    event.get('timestamp'),
                                    1 if event.get('executed') else 0,
                                    json.dumps(event.get('trade_result', {}), ensure_ascii=False),
                                    json.dumps(event, ensure_ascii=False)
                                ))
                            
                            synced_count += 1
                            
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON in {file_path}: {e}")
                            continue
                
                conn.commit()
                
            except Exception as e:
                logger.error(f"Error syncing {event_type} from {file_path}: {e}")
        
        conn.close()
        logger.info(f"Synced {synced_count} {event_type} events to SQLite")
        return synced_count
    
    def _extract_date_from_filename(self, file_path: Path) -> date:
        """Extract date from filename like trades_2024-01-01.jsonl."""
        try:
            date_str = file_path.stem.split('_')[-1]
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, IndexError):
            return date(2000, 1, 1)  # Very old date if can't parse
    
    async def sync_all(self, days_back: Optional[int] = None) -> Dict[str, int]:
        """
        Sync all data types to SQLite.
        
        Args:
            days_back: Number of days to sync (None = all)
        
        Returns:
            Dictionary with sync counts
        """
        results = {}
        
        results['trades'] = await self.sync_trades(days_back=days_back)
        results['ai_decisions'] = await self.sync_analytics('ai_decisions', days_back=days_back)
        results['market_conditions'] = await self.sync_analytics('market_conditions', days_back=days_back)
        results['anomalies'] = await self.sync_analytics('anomalies', days_back=days_back)
        results['decision_results'] = await self.sync_analytics('decision_results', days_back=days_back)
        
        logger.info(f"Sync complete: {results}")
        return results
    
    def get_trade_by_id(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """Get trade by ID from SQLite (returns full JSON for compatibility)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT full_data FROM trades WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def get_decisions_by_symbol(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get AI decisions for symbol from SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT full_data FROM ai_decisions 
            WHERE symbol = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (symbol, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [json.loads(row[0]) for row in rows]


async def main():
    """Main entry point for manual sync."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync JSONL data to SQLite')
    parser.add_argument('--days', type=int, help='Number of days to sync (default: all)')
    parser.add_argument('--type', choices=['trades', 'ai_decisions', 'market_conditions', 'anomalies', 'decision_results', 'all'],
                       default='all', help='Type of data to sync')
    
    args = parser.parse_args()
    
    sync = SQLiteSync()
    
    if args.type == 'all':
        results = await sync.sync_all(days_back=args.days)
        print(f"Sync complete: {results}")
    elif args.type == 'trades':
        count = await sync.sync_trades(days_back=args.days)
        print(f"Synced {count} trades")
    else:
        count = await sync.sync_analytics(args.type, days_back=args.days)
        print(f"Synced {count} {args.type} events")


if __name__ == "__main__":
    asyncio.run(main())

