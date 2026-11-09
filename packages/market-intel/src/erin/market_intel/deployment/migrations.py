"""Database Migrations - Schema versioning and migration management."""

import asyncio
import hashlib
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Any, Callable, TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MigrationStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass
class Migration:
    """Database migration definition."""
    version: str
    name: str
    description: str = ""
    up_sql: str = ""
    down_sql: str = ""
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    checksum: str = ""
    
    def __post_init__(self):
        if not self.checksum and self.up_sql:
            self.checksum = hashlib.sha256(self.up_sql.encode()).hexdigest()[:16]


@dataclass
class MigrationRecord:
    """Migration execution record."""
    version: str
    name: str
    status: str
    applied_at: datetime
    execution_time_ms: float
    checksum: str
    error_message: str = ""


class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self, db_path: str = "~/.erin/migrations.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrations: Dict[str, Migration] = {}
        self._lock = asyncio.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize migration tracking database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                version TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                applied_at TEXT,
                execution_time_ms REAL,
                checksum TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_migrations_status ON migrations(status)")
        conn.commit()
        conn.close()
    
    def register_migration(self, migration: Migration):
        """Register a migration."""
        if migration.version in self._migrations:
            raise ValueError(f"Migration version {migration.version} already registered")
        
        self._migrations[migration.version] = migration
        logger.info(f"Registered migration {migration.version}: {migration.name}")
    
    def register_migration_sql(self, version: str, name: str, up_sql: str, 
                               down_sql: str = "", description: str = "",
                               dependencies: List[str] = None):
        """Register a migration from SQL strings."""
        migration = Migration(
            version=version,
            name=name,
            description=description,
            up_sql=up_sql,
            down_sql=down_sql,
            dependencies=dependencies or [],
        )
        self.register_migration(migration)
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        # Get applied migrations
        applied = {}
        cursor = conn.execute("SELECT version, status, checksum FROM migrations WHERE status = 'COMPLETED'")
        for row in cursor.fetchall():
            applied[row["version"]] = row["checksum"]
        
        # Find pending migrations
        pending = []
        for version, migration in sorted(self._migrations.items()):
            if migration.version not in applied:
                # Check dependencies
                deps_satisfied = all(dep in applied for dep in migration.dependencies)
                if deps_satisfied:
                    pending.append(migration)
        
        return pending
    
    def get_applied_migrations(self) -> List[Dict]:
        """Get list of applied migrations."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM migrations WHERE status = 'COMPLETED' ORDER BY applied_at")
        migrations = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return migrations
    
    async def run_migrations(self, target_version: str = None, dry_run: bool = False) -> List:
        """Run pending migrations up to target version."""
        pending = self.get_pending_migrations()
        
        if target_version:
            # Filter to target version
            filtered = []
            for m in self._migrations.values():
                if m.version <= target_version:
                    filtered.append(m)
                else:
                    break
            pending = [m for m in pending if m.version <= target_version]
        
        results = []
        for migration in pending:
            record = await self._execute_migration(migration)
            if record.status == "FAILED":
                logger.error(f"Migration {migration.version} failed: {record.error_message}")
                break
            results.append(record)
        
        return results
    
    async def _execute_migration(self, migration: Migration) -> MigrationRecord:
        """Execute a single migration."""
        start_time = time.time()
        record = MigrationRecord(
            version=migration.version,
            name=migration.name,
            status=MigrationStatus.RUNNING,
            applied_at=datetime.utcnow(),
            execution_time_ms=0,
            checksum=migration.checksum,
        )
        
        try:
            # Execute up migration
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("BEGIN TRANSACTION")
            conn.execute(migration.up_sql)
            conn.commit()
            conn.close()
            
            # Record success
            record.status = MigrationStatus.COMPLETED
            record.execution_time_ms = (time.time() - start_time) * 1000
            self._record_migration(record)
            
        except Exception as e:
            record.status = MigrationStatus.FAILED
            record.error_message = str(e)
            record.execution_time_ms = (time.time() - start_time) * 1000
            self._record_migration(record)
            raise
        
        return record
    
    def _record_migration(self, record: MigrationRecord):
        """Record migration result in database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO migrations 
            (version, name, description, status, applied_at, execution_time_ms, checksum, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.version, record.name, record.description, record.status,
            record.applied_at.isoformat(), record.execution_time_ms,
            record.checksum, record.error_message
        ))
        conn.commit()
        conn.close()
    
    async def rollback(self, target_version: str) -> List:
        """Rollback migrations to target version."""
        # Get migrations after target version
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT version FROM migrations WHERE status = 'COMPLETED' AND version > ? ORDER BY version DESC",
            (target_version,)
        )
        to_rollback = [row["version"] for row in cursor.fetchall()]
        conn.close()
        
        results = []
        for version in to_rollback:
            migration = self._migrations.get(version)
            if not migration or not migration.down_sql:
                logger.warning(f"No down migration for {version}")
                continue
            
            try:
                conn = sqlite3.connect(str(self.db_path))
                conn.execute("BEGIN TRANSACTION")
                conn.execute(migration.down_sql)
                conn.commit()
                conn.close()
                
                # Update record
                conn = sqlite3.connect(str(self.db_path))
                conn.execute(
                    "UPDATE migrations SET status = 'ROLLED_BACK' WHERE version = ?",
                    (version,)
                )
                conn.commit()
                conn.close()
                
                logger.info(f"Rolled back migration {version}")
            except Exception as e:
                logger.error(f"Rollback {version} failed: {e}")
                raise
        
        return []
    
    def get_migration_status(self) -> Dict:
        """Get migration status summary."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        total = conn.execute("SELECT COUNT(*) FROM migrations").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM migrations WHERE status = 'COMPLETED'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM migrations WHERE status = 'FAILED'").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM migrations WHERE status = 'PENDING'").fetchone()[0]
        
        conn.close()
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
        }


def create_migration_manager(db_path: str = "~/.erin/migrations.db") -> MigrationManager:
    return MigrationManager(db_path)


def run_migrations(db_path: str = "~/.erin/migrations.db", target_version: str = None) -> List:
    """Run all pending migrations."""
    manager = create_migration_manager(db_path)
    return list(manager.run_migrations(target_version))