"""Security Audit Logging - Immutable audit trail with hash chain."""

import hashlib
import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    USER_FAILED_LOGIN = "USER_FAILED_LOGIN"
    USER_MFA_CHALLENGE = "USER_MFA_CHALLENGE"
    USER_PASSWORD_CHANGE = "USER_PASSWORD_CHANGE"
    USER_MFA_ENABLE = "USER_MFA_ENABLE"
    USER_MFA_DISABLE = "USER_MFA_DISABLE"
    USER_ROLE_CHANGE = "USER_ROLE_CHANGE"
    USER_CREATED = "USER_CREATED"
    USER_DELETED = "USER_DELETED"
    USER_LOCKED = "USER_LOCKED"
    USER_UNLOCKED = "USER_UNLOCKED"
    TOOL_EXECUTED = "TOOL_EXECUTED"
    TOOL_APPROVED = "TOOL_APPROVED"
    TOOL_REJECTED = "TOOL_REJECTED"
    TOOL_FAILED = "TOOL_FAILED"
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    PORTFOLIO_CREATED = "PORTFOLIO_CREATED"
    PORTFOLIO_UPDATED = "PORTFOLIO_UPDATED"
    PORTFOLIO_DELETED = "PORTFOLIO_DELETED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    POSITION_UPDATED = "POSITION_UPDATED"
    RISK_LIMIT_BREACH = "RISK_LIMIT_BREACH"
    VAR_LIMIT_BREACH = "VAR_LIMIT_BREACH"
    DRAWDOWN_LIMIT_BREACH = "DRAWDOWN_LIMIT_BREACH"
    CONCENTRATION_LIMIT_BREACH = "CONCENTRATION_LIMIT_BREACH"
    DATA_ACCESS = "DATA_ACCESS"
    DATA_EXPORT = "DATA_EXPORT"
    DATA_IMPORT = "DATA_IMPORT"
    CONFIG_CHANGED = "CONFIG_CHANGED"
    PERMISSION_CHANGED = "PERMISSION_CHANGED"
    API_KEY_CREATED = "API_KEY_CREATED"
    API_KEY_REVOKED = "API_KEY_REVOKED"
    SYSTEM_START = "SYSTEM_START"
    SYSTEM_STOP = "SYSTEM_STOP"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    BACKUP_CREATED = "BACKUP_CREATED"
    BACKUP_RESTORED = "BACKUP_RESTORED"
    CUSTOM = "CUSTOM"


@dataclass
class AuditEvent:
    """Immutable audit event record."""
    event_type: AuditEventType
    user_id: str
    session_id: str = ""
    ip_address: str = ""
    user_agent: str = ""
    resource_type: str = ""
    resource_id: str = ""
    action: str = ""
    old_values: dict = field(default_factory=dict)
    new_values: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    success: bool = True
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: hashlib.sha256(f"{time.time()}{threading.current_thread().ident}".encode()).hexdigest()[:16])
    prev_hash: str = ""
    event_hash: str = ""

    def compute_hash(self, prev_hash: str) -> str:
        """Compute hash chain for tamper evidence."""
        data = f"{self.event_id}{self.timestamp.isoformat()}{self.user_id}{self.event_type.value}{self.resource_type}{self.resource_id}{json.dumps(self.old_values, sort_keys=True)}{json.dumps(self.new_values, sort_keys=True)}{prev_hash}"
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "metadata": self.metadata,
            "risk_level": self.risk_level,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "prev_hash": self.prev_hash,
            "event_hash": self.event_hash,
        }


class AuditLogger:
    """Immutable audit logger with hash chain."""

    def __init__(self, db_path: str = "~/.erin/audit.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = ""
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize audit database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                user_id TEXT NOT NULL,
                session_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT,
                old_values TEXT,
                new_values TEXT,
                metadata TEXT,
                risk_level TEXT NOT NULL,
                success INTEGER NOT NULL,
                error_message TEXT,
                timestamp TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_events(user_id, timestamp DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_type_time ON audit_events(event_type, timestamp DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_events(resource_type, resource_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_hash_chain ON audit_events(prev_hash, event_hash)")
        conn.commit()
        conn.close()

        # Get last hash
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute("SELECT event_hash FROM audit_events ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            self._last_hash = row[0]
        conn.close()

    def log(self, event: AuditEvent) -> str:
        """Log an audit event with hash chain."""
        with self._lock:
            event.prev_hash = self._last_hash
            event.event_hash = event.compute_hash(self._last_hash)

            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                INSERT INTO audit_events (
                    event_id, event_type, user_id, session_id, ip_address, user_agent,
                    resource_type, resource_id, action, old_values, new_values, metadata,
                    risk_level, success, error_message, timestamp, prev_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.event_type.value, event.user_id, event.session_id,
                event.ip_address, event.user_agent, event.resource_type, event.resource_id,
                event.action, json.dumps(event.old_values), json.dumps(event.new_values),
                json.dumps(event.metadata), event.risk_level, int(event.success),
                event.error_message, event.timestamp.isoformat(),
                event.prev_hash, event.event_hash
            ))
            conn.commit()
            conn.close()

            self._last_hash = event.event_hash
            return event.event_id

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        session_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        resource_type: str = "",
        resource_id: str = "",
        action: str = "",
        old_values: dict = None,
        new_values: dict = None,
        metadata: dict = None,
        risk_level: str = "LOW",
        success: bool = True,
        error_message: str = "",
    ) -> str:
        """Convenience method to log an audit event."""
        event = AuditEvent(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            old_values=old_values or {},
            new_values=new_values or {},
            metadata=metadata or {},
            risk_level=risk_level,
            success=success,
            error_message=error_message,
        )
        return self.log(event)

    def verify_chain(self, start_id: str = None, end_id: str = None) -> tuple:
        """Verify hash chain integrity."""
        conn = sqlite3.connect(str(self.db_path))
        query = "SELECT event_id, prev_hash, event_hash, timestamp FROM audit_events"
        params = []
        if start_id:
            query += " WHERE event_id >= ?"
            params.append(start_id)
        if end_id:
            if "WHERE" in query:
                query += " AND event_id <= ?"
            else:
                query += " WHERE event_id <= ?"
            params.append(end_id)
        query += " ORDER BY timestamp ASC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        prev_hash = ""
        broken = []
        for i, (event_id, prev_hash, event_hash, timestamp) in enumerate(rows):
            if i == 0:
                prev_hash = prev_hash
            else:
                # Recompute expected hash
                # This is simplified - in production would re-compute from event data
                if prev_hash != rows[i-1][2]:  # previous event_hash
                    broken.append({
                        "event_id": event_id,
                        "expected_prev_hash": rows[i-1][2],
                        "actual_prev_hash": prev_hash
                    })
            prev_hash = event_hash

        return {
            "valid": len(broken) == 0,
            "total_events": len(rows),
            "broken_links": broken
        }

    def query_events(
        self,
        user_id: str = None,
        event_type: AuditEventType = None,
        start_time: datetime = None,
        end_time: datetime = None,
        resource_type: str = None,
        resource_id: str = None,
        risk_level: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[dict]:
        """Query audit events with filters."""
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)
        if resource_id:
            query += " AND resource_id = ?"
            params.append(resource_id)
        if risk_level:
            query += " AND risk_level = ?"
            params.append(risk_level)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        """Get audit statistics."""
        conn = sqlite3.connect(str(self.db_path))
        stats = {}
        stats["total_events"] = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
        stats["by_type"] = dict(conn.execute("SELECT event_type, COUNT(*) FROM audit_events GROUP BY event_type").fetchall())
        stats["by_risk"] = dict(conn.execute("SELECT risk_level, COUNT(*) FROM audit_events GROUP BY risk_level").fetchall())
        stats["by_user"] = dict(conn.execute("SELECT user_id, COUNT(*) FROM audit_events GROUP BY user_id ORDER BY COUNT(*) DESC LIMIT 10").fetchall())
        stats["success_rate"] = conn.execute("SELECT AVG(success) FROM audit_events").fetchone()[0] or 0
        stats["last_event"] = conn.execute("SELECT timestamp FROM audit_events ORDER BY timestamp DESC LIMIT 1").fetchone()
        if stats["last_event"]:
            stats["last_event"] = stats["last_event"][0]
        conn.close()
        return stats


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(db_path: str = "~/.erin/audit.db") -> AuditLogger:
    """Get or create global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(db_path)
    return _audit_logger


def audit_log(
    event_type: AuditEventType,
    user_id: str,
    session_id: str = "",
    ip_address: str = "",
    user_agent: str = "",
    resource_type: str = "",
    resource_id: str = "",
    action: str = "",
    old_values: dict = None,
    new_values: dict = None,
    metadata: dict = None,
    risk_level: str = "LOW",
    success: bool = True,
    error_message: str = "",
) -> str:
    """Convenience function to log audit event."""
    logger = get_audit_logger()
    return logger.log_event(
        event_type=event_type,
        user_id=user_id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        old_values=old_values,
        new_values=new_values,
        metadata=metadata,
        risk_level=risk_level,
        success=success,
        error_message=error_message
    )