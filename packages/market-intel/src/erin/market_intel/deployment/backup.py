"""Backup & Restore - Automated backup and disaster recovery."""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import tarfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Any, Callable, TYPE_CHECKING
import asyncio
import subprocess

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class BackupType(str, Enum):
    FULL = "FULL"
    INCREMENTAL = "INCREMENTAL"
    DIFFERENTIAL = "DIFFERENTIAL"
    SNAPSHOT = "SNAPSHOT"


class BackupStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class BackupConfig:
    source_paths: List[str] = field(default_factory=list)
    destination: str = "~/.erin/backups"
    backup_type: BackupType = BackupType.INCREMENTAL
    compression: bool = True
    compression_level: int = 6
    encryption: bool = False
    encryption_key: str = ""
    max_backups: int = 30
    max_age_days: int = 90
    schedule: str = "0 2 * * *"  # Daily at 2 AM
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.log", "*.tmp", "*.cache", "__pycache__", ".git", "node_modules"
    ])
    verify_after_backup: bool = True
    notify_on_success: bool = True
    notify_on_failure: bool = True
    retention_policy: Dict = field(default_factory=dict)


@dataclass
class BackupResult:
    backup_id: str = field(default_factory=lambda: f"bkp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    backup_type: BackupType = BackupType.FULL
    source_paths: List[str] = field(default_factory=list)
    destination: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    size_bytes: int = 0
    compressed_size_bytes: int = 0
    file_count: int = 0
    status: BackupStatus = BackupStatus.PENDING
    error_message: str = ""
    checksum: str = ""
    metadata: Dict = field(default_factory=dict)
    
    @property
    def compression_ratio(self) -> float:
        if self.size_bytes == 0:
            return 0.0
        return self.compressed_size_bytes / self.size_bytes


@dataclass
class RestoreResult:
    restore_id: str = field(default_factory=lambda: f"rst_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    backup_id: str = ""
    destination: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    files_restored: int = 0
    bytes_restored: int = 0
    status: BackupStatus = BackupStatus.PENDING
    error_message: str = ""
    verified: bool = False


class BackupManager:
    """Manages backup operations with scheduling and retention."""
    
    def __init__(self, config: BackupConfig = None):
        self.config = config or BackupConfig()
        self.destination = Path(self.config.destination).expanduser()
        self.destination.mkdir(parents=True, exist_ok=True)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._history: List[BackupResult] = []
        self._load_history()
    
    def _load_history(self):
        """Load backup history from metadata files."""
        history_file = self.destination / "backup_history.json"
        if history_file.exists():
            try:
                data = json.loads(history_file.read_text())
                self._history = [BackupResult(**item) for item in data]
            except Exception as e:
                logger.warning(f"Failed to load backup history: {e}")
                self._history = []
    
    def _save_history(self):
        """Save backup history to metadata file."""
        try:
            history_file = self.destination / "backup_history.json"
            data = []
            for result in self._history:
                data.append({
                    "backup_id": result.backup_id,
                    "backup_type": result.backup_type.value,
                    "source_paths": result.source_paths,
                    "destination": result.destination,
                    "started_at": result.started_at.isoformat(),
                    "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                    "duration_seconds": result.duration_seconds,
                    "size_bytes": result.size_bytes,
                    "compressed_size_bytes": result.compressed_size_bytes,
                    "file_count": result.file_count,
                    "status": result.status.value,
                    "error_message": result.error_message,
                    "checksum": result.checksum,
                    "metadata": result.metadata,
                })
            history_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save backup history: {e}")
    
    async def create_backup(self, backup_type: BackupType = None, 
                           source_paths: List[str] = None) -> BackupResult:
        """Create a backup."""
        if self._running:
            raise RuntimeError("Backup already in progress")
        
        self._running = True
        backup_type = backup_type or self.config.backup_type
        source_paths = source_paths or self.config.source_paths
        
        result = BackupResult(
            backup_type=backup_type,
            source_paths=source_paths,
            destination=str(self.destination),
        )
        
        self._running = True
        start_time = time.time()
        
        try:
            # Determine backup file path
            backup_file = self.destination / f"{result.backup_id}.tar.gz"
            
            # Create archive
            await self._create_archive(source_paths, backup_file, result)
            
            # Calculate checksum
            result.checksum = await self._calculate_checksum(Path(self.destination) / f"{result.backup_id}.tar.gz")
            
            # Verify if enabled
            if self.config.verify_after_backup:
                await self._verify_backup(result)
            
            result.completed_at = datetime.utcnow()
            result.duration_seconds = time.time() - time.mktime(datetime.utcnow().timetuple())
            result.status = BackupStatus.COMPLETED
            
        except Exception as e:
            result.status = BackupStatus.FAILED
            result.error_message = str(e)
            logger.error(f"Backup failed: {e}")
        finally:
            self._running = False
            result.duration_seconds = time.time() - time.mktime(datetime.utcnow().timetuple())
            self._history.append(result)
            self._save_history()
            self._cleanup_old_backups()
        
        return result
    
    async def _create_archive(self, source_paths: List[str], destination: Path, result: BackupResult):
        """Create compressed archive of source paths."""
        total_size = 0
        file_count = 0
        
        with tarfile.open(destination, "w:gz", compresslevel=self.config.compression_level) as tar:
            for source_path in source_paths:
                source = Path(source_path).expanduser()
                if not source.exists():
                    logger.warning(f"Source path does not exist: {source}")
                    continue
                
                if source.is_file():
                    tar.add(source, arcname=source.name)
                    file_count = 1
                    total_size += source.stat().st_size
                else:
                    for file_path in source.rglob("*"):
                        if file_path.is_file():
                            # Check exclude patterns
                            excluded = False
                            for pattern in self.config.exclude_patterns:
                                if file_path.match(pattern):
                                    excluded = True
                                    break
                            if excluded:
                                continue
                            
                            arcname = file_path.relative_to(source.parent)
                            tar.add(file_path, arcname=arcname)
                            file_count += 1
                            total_size += file_path.stat().st_size
        
        result.size_bytes = total_size
        result.compressed_size_bytes = destination.stat().st_size
        result.file_count = file_count
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    async def _verify_backup(self, result: BackupResult):
        """Verify backup integrity."""
        backup_file = Path(result.destination) / f"{result.backup_id}.tar.gz"
        
        # Verify checksum
        actual_checksum = await self._calculate_checksum(backup_file)
        if actual_checksum != result.checksum:
            raise ValueError(f"Checksum mismatch: expected {result.checksum}, got {actual_checksum}")
        
        # Test extraction
        with tarfile.open(backup_file, "r:gz") as tar:
            members = tar.getmembers()
            if not members:
                raise ValueError("Backup archive is empty")
        
        logger.info(f"Backup verification passed for {result.backup_id}")
    
    async def _cleanup_old_backups(self):
        """Remove old backups based on retention policy."""
        backups = sorted(
            [f for f in self.destination.glob("*.tar.gz")],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        # Remove by count
        if len(backups) > self.config.max_backups:
            for old_backup in backups[self.config.max_backups:]:
                old_backup.unlink()
                meta_file = old_backup.with_suffix(".meta.json")
                if meta_file.exists():
                    meta_file.unlink()
                logger.info(f"Removed old backup: {old_backup.name}")
        
        # Remove by age
        cutoff = datetime.utcnow() - timedelta(days=self.config.max_age_days)
        for backup in backups:
            if datetime.fromtimestamp(backup.stat().st_mtime) < cutoff:
                backup.unlink()
                meta_file = backup.with_suffix(".meta.json")
                if meta_file.exists():
                    meta_file.unlink()
                logger.info(f"Removed expired backup: {backup.name}")
    
    async def list_backups(self) -> List[BackupResult]:
        """List all backups in history."""
        return self._history.copy()
    
    async def get_latest_backup(self, backup_type: BackupType = None) -> Optional[BackupResult]:
        """Get the most recent backup."""
        backups = [b for b in self._history if b.status == BackupStatus.COMPLETED]
        if backup_type:
            backups = [b for b in backups if b.backup_type == backup_type]
        return backups[0] if backups else None
    
    async def restore_backup(self, backup_id: str, destination: str, 
                            verify: bool = True, overwrite: bool = False) -> 'RestoreResult':
        """Restore from a backup."""
        backup = self.get_backup(backup_id)
        if not backup:
            raise ValueError(f"Backup {backup_id} not found")
        
        if backup.status != BackupStatus.COMPLETED:
            raise ValueError(f"Backup {backup_id} is not completed")
        
        result = RestoreResult(
            backup_id=backup_id,
            destination=destination,
        )
        
        dest_path = Path(destination).expanduser()
        dest_path.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        
        try:
            backup_file = Path(backup.destination) / f"{backup_id}.tar.gz"
            
            if verify:
                await self._verify_backup(backup)
            
            # Extract archive
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(dest_path)
            
            # Count restored files
            restored_files = list(dest_path.rglob("*"))
            result.files_restored = len([f for f in restored_files if f.is_file()])
            result.bytes_restored = sum(f.stat().st_size for f in restored_files if f.is_file())
            result.status = BackupStatus.COMPLETED
            result.verified = True
            
        except Exception as e:
            result.status = BackupStatus.FAILED
            result.error_message = str(e)
            logger.error(f"Restore failed: {e}")
            raise
        finally:
            result.completed_at = datetime.utcnow()
            result.duration_seconds = time.time() - start_time
        
        return result
    
    def get_backup_stats(self) -> Dict:
        """Get backup statistics."""
        completed = [b for b in self._history if b.status == BackupStatus.COMPLETED]
        failed = [b for b in self._history if b.status == BackupStatus.FAILED]
        
        total_size = sum(b.size_bytes for b in completed)
        total_compressed = sum(b.compressed_size_bytes for b in completed)
        
        return {
            "total_backups": len(self._history),
            "completed": len(completed),
            "failed": len(failed),
            "total_size_bytes": total_size,
            "total_compressed_bytes": total_compressed,
            "compression_ratio": total_compressed / total_size if total_size > 0 else 0,
            "last_backup": completed[-1].completed_at.isoformat() if completed else None,
            "next_scheduled": "Based on cron schedule",
        }
    
    async def schedule_backups(self):
        """Start scheduled backup task."""
        if self._task:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
    
    async def stop_scheduler(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _scheduler_loop(self):
        while self._running:
            try:
                # Check if it's time for scheduled backup
                # Simplified: run every 24 hours at 2 AM
                now = datetime.utcnow()
                next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                wait_seconds = (next_run - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                if self._running:
                    await self.create_backup()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(3600)  # Check every hour
    
    def get_history(self) -> List[BackupResult]:
        return self._history.copy()
    
    def get_backup(self, backup_id: str) -> Optional[BackupResult]:
        for b in self._history:
            if b.backup_id == backup_id:
                return b
        return None


class RestoreManager:
    """Manages restore operations from backups."""
    
    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
    
    async def restore(self, backup_id: str, destination: str, 
                     verify: bool = True, overwrite: bool = False) -> RestoreResult:
        """Restore from a backup."""
        backup = self.backup_manager.get_backup(backup_id)
        if not backup:
            raise ValueError(f"Backup {backup_id} not found")
        
        if backup.status != BackupStatus.COMPLETED:
            raise ValueError(f"Backup {backup_id} is not completed")
        
        result = RestoreResult(
            backup_id=backup_id,
            destination=destination,
        )
        
        dest_path = Path(destination).expanduser()
        dest_path.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        
        try:
            backup_file = Path(backup.destination) / f"{backup_id}.tar.gz"
            
            if verify:
                await self.backup_manager._verify_backup(backup)
            
            # Extract archive
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(dest_path)
            
            # Count restored files
            restored_files = list(dest_path.rglob("*"))
            result.files_restored = len([f for f in restored_files if f.is_file()])
            result.bytes_restored = sum(f.stat().st_size for f in restored_files if f.is_file())
            result.status = BackupStatus.COMPLETED
            result.verified = True
            
        except Exception as e:
            result.status = BackupStatus.FAILED
            result.error_message = str(e)
            logger.error(f"Restore failed: {e}")
            raise
        finally:
            result.completed_at = datetime.utcnow()
            result.duration_seconds = time.time() - start_time
        
        return result


def create_backup_manager(config: BackupConfig = None) -> BackupManager:
    return BackupManager(config)


def create_restore_manager(backup_manager: BackupManager) -> RestoreManager:
    return RestoreManager(backup_manager)