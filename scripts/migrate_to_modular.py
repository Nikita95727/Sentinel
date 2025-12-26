#!/usr/bin/env python3
"""
Migration script for modular architecture.
Safely migrates data and ensures backward compatibility.
"""
import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages migration to modular architecture."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.backup_dir = self.project_root / "backup" / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Old paths (pre-modular)
        self.old_storage = self.project_root / "storage"
        self.old_trades = self.old_storage / "trades"
        self.old_analytics = self.old_storage / "analytics"
        
        # New paths (modular)
        self.new_conservative_storage = self.project_root / "storage" / "conservative"
        self.new_conservative_trades = self.new_conservative_storage / "trades"
        self.new_conservative_analytics = self.new_conservative_storage / "analytics"
    
    def create_backup(self):
        """Create backup of all critical data."""
        logger.info("=" * 80)
        logger.info("STEP 1: Creating backup of all data")
        logger.info("=" * 80)
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup storage directory
        if self.old_storage.exists():
            backup_storage = self.backup_dir / "storage"
            logger.info(f"Backing up {self.old_storage} to {backup_storage}")
            shutil.copytree(self.old_storage, backup_storage, dirs_exist_ok=True)
            logger.info(f"✅ Backup created: {backup_storage}")
        
        # Backup logs
        logs_dir = self.project_root / "logs"
        if logs_dir.exists():
            backup_logs = self.backup_dir / "logs"
            logger.info(f"Backing up {logs_dir} to {backup_logs}")
            shutil.copytree(logs_dir, backup_logs, dirs_exist_ok=True)
            logger.info(f"✅ Logs backed up")
        
        logger.info(f"✅ Backup complete: {self.backup_dir}")
        return True
    
    def migrate_trade_files(self):
        """Migrate trade files from old location to new modular structure."""
        logger.info("=" * 80)
        logger.info("STEP 2: Migrating trade files")
        logger.info("=" * 80)
        
        # Ensure new directories exist
        self.new_conservative_trades.mkdir(parents=True, exist_ok=True)
        self.new_conservative_analytics.mkdir(parents=True, exist_ok=True)
        
        migrated_count = 0
        
        # Migrate trade files
        if self.old_trades.exists():
            logger.info(f"Migrating trades from {self.old_trades}")
            for file in self.old_trades.glob("*.jsonl"):
                dest = self.new_conservative_trades / file.name
                if not dest.exists():
                    shutil.copy2(file, dest)
                    logger.info(f"  ✅ Migrated: {file.name}")
                    migrated_count += 1
                else:
                    logger.info(f"  ⏭️  Skipped (exists): {file.name}")
        
        # Migrate analytics files
        if self.old_analytics.exists():
            logger.info(f"Migrating analytics from {self.old_analytics}")
            for file in self.old_analytics.glob("*.jsonl"):
                dest = self.new_conservative_analytics / file.name
                if not dest.exists():
                    shutil.copy2(file, dest)
                    logger.info(f"  ✅ Migrated: {file.name}")
                    migrated_count += 1
                else:
                    logger.info(f"  ⏭️  Skipped (exists): {file.name}")
        
        logger.info(f"✅ Migrated {migrated_count} files")
        return True
    
    def verify_data_integrity(self):
        """Verify that all data was migrated correctly."""
        logger.info("=" * 80)
        logger.info("STEP 3: Verifying data integrity")
        logger.info("=" * 80)
        
        issues = []
        
        # Check trade files
        if self.old_trades.exists():
            old_trade_files = list(self.old_trades.glob("*.jsonl"))
            for old_file in old_trade_files:
                new_file = self.new_conservative_trades / old_file.name
                if not new_file.exists():
                    issues.append(f"Missing trade file: {old_file.name}")
                else:
                    # Compare file sizes
                    old_size = old_file.stat().st_size
                    new_size = new_file.stat().st_size
                    if old_size != new_size:
                        issues.append(f"Size mismatch: {old_file.name} ({old_size} vs {new_size})")
        
        # Check analytics files
        if self.old_analytics.exists():
            old_analytics_files = list(self.old_analytics.glob("*.jsonl"))
            for old_file in old_analytics_files:
                new_file = self.new_conservative_analytics / old_file.name
                if not new_file.exists():
                    issues.append(f"Missing analytics file: {old_file.name}")
                else:
                    old_size = old_file.stat().st_size
                    new_size = new_file.stat().st_size
                    if old_size != new_size:
                        issues.append(f"Size mismatch: {old_file.name} ({old_size} vs {new_size})")
        
        if issues:
            logger.error("❌ Data integrity issues found:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False
        else:
            logger.info("✅ All data verified successfully")
            return True
    
    def create_symlinks(self):
        """Create symlinks for backward compatibility (optional)."""
        logger.info("=" * 80)
        logger.info("STEP 4: Creating backward compatibility symlinks (optional)")
        logger.info("=" * 80)
        
        # Don't create symlinks - new structure is clear
        # But keep old directories for reference
        logger.info("⏭️  Skipping symlinks (using new structure directly)")
        return True
    
    def generate_migration_report(self):
        """Generate migration report."""
        logger.info("=" * 80)
        logger.info("STEP 5: Generating migration report")
        logger.info("=" * 80)
        
        report = {
            "migration_time": datetime.now().isoformat(),
            "backup_location": str(self.backup_dir),
            "old_structure": {
                "trades": str(self.old_trades) if self.old_trades.exists() else None,
                "analytics": str(self.old_analytics) if self.old_analytics.exists() else None,
            },
            "new_structure": {
                "conservative_trades": str(self.new_conservative_trades),
                "conservative_analytics": str(self.new_conservative_analytics),
            },
            "files_migrated": {
                "trades": len(list(self.new_conservative_trades.glob("*.jsonl"))) if self.new_conservative_trades.exists() else 0,
                "analytics": len(list(self.new_conservative_analytics.glob("*.jsonl"))) if self.new_conservative_analytics.exists() else 0,
            }
        }
        
        report_file = self.backup_dir / "migration_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✅ Migration report saved: {report_file}")
        logger.info(f"   Trades: {report['files_migrated']['trades']} files")
        logger.info(f"   Analytics: {report['files_migrated']['analytics']} files")
        
        return report
    
    def run_migration(self):
        """Run complete migration process."""
        logger.info("=" * 80)
        logger.info("MIGRATION TO MODULAR ARCHITECTURE")
        logger.info("=" * 80)
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Backup directory: {self.backup_dir}")
        logger.info("")
        
        try:
            # Step 1: Backup
            if not self.create_backup():
                raise Exception("Backup failed")
            
            # Step 2: Migrate files
            if not self.migrate_trade_files():
                raise Exception("Migration failed")
            
            # Step 3: Verify
            if not self.verify_data_integrity():
                raise Exception("Data integrity check failed")
            
            # Step 4: Symlinks (optional)
            self.create_symlinks()
            
            # Step 5: Report
            report = self.generate_migration_report()
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"Backup location: {self.backup_dir}")
            logger.info("")
            logger.info("⚠️  IMPORTANT:")
            logger.info("   1. Verify bot works correctly")
            logger.info("   2. Check that new files are being created in new locations")
            logger.info("   3. Keep backup for at least 7 days")
            logger.info("   4. Old files are preserved - you can remove them after verification")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            logger.error("")
            logger.error("⚠️  ROLLBACK INSTRUCTIONS:")
            logger.error(f"   Restore from backup: {self.backup_dir}")
            raise


def main():
    """Main entry point."""
    import sys
    
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    
    migrator = MigrationManager(project_root)
    
    try:
        migrator.run_migration()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

