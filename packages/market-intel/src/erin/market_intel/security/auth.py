"""Authentication & Authorization - Multi-factor auth, RBAC, session management."""

import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable, TYPE_CHECKING
import pyotp
import qrcode
from io import BytesIO
import base64

if TYPE_CHECKING:
    pass

from erin.market_intel.security.audit import AuditEventType, audit_log


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class Permission(str, Enum):
    """System permissions."""
    # Market data
    MARKET_DATA_READ = "market_data:read"
    MARKET_DATA_WRITE = "market_data:write"

    # Fundamental data
    FUNDAMENTAL_READ = "fundamental:read"
    FUNDAMENTAL_WRITE = "fundamental:write"

    # Trading
    TRADING_READ = "trading:read"
    TRADING_WRITE = "trading:write"
    ORDER_PLACE = "order:place"
    ORDER_CANCEL = "order:cancel"
    ORDER_MODIFY = "order:modify"

    # Portfolio
    PORTFOLIO_READ = "portfolio:read"
    PORTFOLIO_WRITE = "portfolio:write"
    PORTFOLIO_MANAGE = "portfolio:manage"

    # Risk
    RISK_READ = "risk:read"
    RISK_WRITE = "risk:write"
    RISK_MANAGE = "risk:manage"

    # Backtesting
    BACKTEST_READ = "backtest:read"
    BACKTEST_WRITE = "backtest:write"
    BACKTEST_RUN = "backtest:run"

    # Quantitative
    QUANT_READ = "quant:read"
    QUANT_WRITE = "quant:write"
    QUANT_MODEL = "quant:model"

    # Research
    RESEARCH_READ = "research:read"
    RESEARCH_WRITE = "research:write"
    REPORT_GENERATE = "report:generate"

    # Administration
    ADMIN_USERS = "admin:users"
    ADMIN_ROLES = "admin:roles"
    ADMIN_AUDIT = "admin:audit"
    ADMIN_CONFIG = "admin:config"
    ADMIN_SYSTEM = "admin:system"

    # Security
    SECURITY_AUDIT = "security:audit"
    SECURITY_KEYS = "security:keys"
    SECURITY_CONFIG = "security:config"

    # Data
    DATA_READ = "data:read"
    DATA_WRITE = "data:write"
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"

    # AI/ML
    AI_CHAT = "ai:chat"
    AI_RESEARCH = "ai:research"
    AI_TOOLS = "ai:tools"
    AI_MODEL = "ai:model"


# Predefined roles with permissions
DEFAULT_ROLES: Dict[str, Set[Permission]] = {
    "super_admin": set(Permission),
    "admin": {
        Permission.MARKET_DATA_READ, Permission.MARKET_DATA_WRITE,
        Permission.FUNDAMENTAL_READ, Permission.FUNDAMENTAL_WRITE,
        Permission.TRADING_READ, Permission.TRADING_WRITE,
        Permission.ORDER_PLACE, Permission.ORDER_CANCEL, Permission.ORDER_MODIFY,
        Permission.PORTFOLIO_READ, Permission.PORTFOLIO_WRITE, Permission.PORTFOLIO_MANAGE,
        Permission.RISK_READ, Permission.RISK_WRITE, Permission.RISK_MANAGE,
        Permission.BACKTEST_READ, Permission.BACKTEST_WRITE, Permission.BACKTEST_RUN,
        Permission.QUANT_READ, Permission.QUANT_WRITE, Permission.QUANT_MODEL,
        Permission.RESEARCH_READ, Permission.RESEARCH_WRITE, Permission.REPORT_GENERATE,
        Permission.ADMIN_USERS, Permission.ADMIN_ROLES, Permission.ADMIN_AUDIT,
        Permission.ADMIN_CONFIG, Permission.ADMIN_SYSTEM,
        Permission.DATA_READ, Permission.DATA_WRITE, Permission.DATA_EXPORT,
        Permission.AI_CHAT, Permission.AI_RESEARCH, Permission.AI_TOOLS,
    },
    "risk_manager": {
        Permission.MARKET_DATA_READ,
        Permission.FUNDAMENTAL_READ,
        Permission.TRADING_READ,
        Permission.PORTFOLIO_READ, Permission.PORTFOLIO_WRITE,
        Permission.RISK_READ, Permission.RISK_WRITE, Permission.RISK_MANAGE,
        Permission.BACKTEST_READ, Permission.BACKTEST_RUN,
        Permission.QUANT_READ, Permission.QUANT_WRITE,
        Permission.RESEARCH_READ, Permission.RESEARCH_WRITE,
    },
    "trader": {
        Permission.MARKET_DATA_READ, Permission.MARKET_DATA_WRITE,
        Permission.TRADING_READ, Permission.TRADING_WRITE,
        Permission.ORDER_PLACE, Permission.ORDER_CANCEL, Permission.ORDER_MODIFY,
        Permission.PORTFOLIO_READ, Permission.PORTFOLIO_WRITE,
        Permission.RISK_READ,
        Permission.BACKTEST_READ, Permission.BACKTEST_RUN,
    },
    "analyst": {
        Permission.MARKET_DATA_READ,
        Permission.FUNDAMENTAL_READ, Permission.FUNDAMENTAL_WRITE,
        Permission.RESEARCH_READ, Permission.RESEARCH_WRITE,
        Permission.REPORT_GENERATE,
        Permission.QUANT_READ, Permission.QUANT_WRITE,
        Permission.BACKTEST_READ, Permission.BACKTEST_WRITE,
    },
    "researcher": {
        Permission.MARKET_DATA_READ,
        Permission.FUNDAMENTAL_READ,
        Permission.RESEARCH_READ, Permission.RESEARCH_WRITE,
        Permission.REPORT_GENERATE,
        Permission.AI_CHAT, Permission.AI_RESEARCH,
    },
    "viewer": {
        Permission.MARKET_DATA_READ,
        Permission.FUNDAMENTAL_READ,
        Permission.PORTFOLIO_READ,
        Permission.RESEARCH_READ,
    },
    "auditor": {
        Permission.ADMIN_AUDIT,
        Permission.DATA_READ,
        Permission.SECURITY_AUDIT,
    },
}


@dataclass
class User:
    """User account."""
    user_id: str = field(default_factory=lambda: f"usr_{secrets.token_hex(12)}")
    username: str = ""
    email: str = ""
    email_verified: bool = False
    password_hash: str = ""
    salt: str = ""
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    roles: List[str] = field(default_factory=list)
    mfa_enabled: bool = False
    mfa_secret: str = ""
    mfa_backup_codes: List[str] = field(default_factory=list)
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    last_password_change: Optional[datetime] = None
    api_keys: List[str] = field(default_factory=list)
    permissions: Set[Permission] = field(default_factory=set)
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_password_change: Optional[datetime] = None
    password_history: List[str] = field(default_factory=list)

    def has_permission(self, permission: Permission) -> bool:
        if permission in self.permissions:
            return True
        for role in self.roles:
            if role in DEFAULT_ROLES and permission in DEFAULT_ROLES[role]:
                return True
        return False

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def add_role(self, role: str) -> bool:
        if role in DEFAULT_ROLES and role not in self.roles:
            self.roles.append(role)
            return True
        return False

    def remove_role(self, role: str) -> bool:
        if role in self.roles:
            self.roles.remove(role)
            return True
        return False

    def get_all_permissions(self) -> Set[Permission]:
        perms = set(self.permissions)
        for role in self.roles:
            if role in DEFAULT_ROLES:
                perms.update(DEFAULT_ROLES[role])
        return perms

    def is_locked(self) -> bool:
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return self.status == UserStatus.LOCKED

    def to_dict(self, include_sensitive: bool = False) -> dict:
        data = {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "email_verified": self.email_verified,
            "status": self.status.value,
            "roles": self.roles,
            "mfa_enabled": self.mfa_enabled,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "failed_login_attempts": self.failed_login_attempts,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "permissions": [p.value for p in self.get_all_permissions()],
        }
        if include_sensitive:
            data["email"] = self.email
            data["mfa_enabled"] = self.mfa_enabled
        return data


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: f"sess_{secrets.token_hex(16)}")
    user_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    last_activity: datetime = field(default_factory=datetime.utcnow)
    ip_address: str = ""
    user_agent: str = ""
    is_active: bool = True
    mfa_verified: bool = False
    permissions: Set[Permission] = field(default_factory=set)
    metadata: Dict = field(default_factory=dict)

    def is_valid(self) -> bool:
        return self.is_active and self.expires_at > datetime.utcnow()

    def refresh(self, duration: timedelta = timedelta(hours=24)):
        self.expires_at = datetime.utcnow() + duration
        self.last_activity = datetime.utcnow()


@dataclass
class ApiKey:
    key_id: str = field(default_factory=lambda: f"key_{secrets.token_hex(16)}")
    key_prefix: str = field(default_factory=lambda: f"erin_{secrets.token_hex(8)}")
    key_hash: str = ""
    name: str = ""
    user_id: str = ""
    permissions: Set[Permission] = field(default_factory=set)
    rate_limit: int = 1000
    ip_whitelist: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    last_used_by: str = ""

    def is_valid(self) -> bool:
        return self.is_active and (self.expires_at is None or self.expires_at > datetime.utcnow())


class PasswordPolicy:
    min_length: int = 12
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special: bool = True
    max_age_days: int = 90
    history_length: int = 5
    min_age_days: int = 1
    lockout_threshold: int = 5
    lockout_duration_minutes: int = 30
    require_mfa: bool = False

    def validate(self, password: str, user: User = None) -> tuple:
        errors = []
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters")
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain uppercase letter")
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain lowercase letter")
        if self.require_digits and not any(c.isdigit() for c in password):
            errors.append("Password must contain digit")
        if self.require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain special character")
        if user and user.password_history:
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), user.salt.encode(), 100000).hex()
            if new_hash in user.password_history:
                errors.append("Password cannot be reused from recent history")
        return len(errors) == 0, errors


class MFAManager:
    def __init__(self, issuer: str = "ERIN"):
        self.issuer = issuer

    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def generate_qr_code(self, username: str, secret: str) -> str:
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(username, issuer=self.issuer)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    def generate_backup_codes(self, count: int = 10) -> List[str]:
        return [secrets.token_hex(4).upper() for _ in range(count)]

    def verify_totp(self, secret: str, code: str, window: int = 1) -> bool:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)

    def verify_backup_code(self, user: User, code: str) -> bool:
        code = code.upper().replace("-", "").replace(" ", "")
        if code in user.mfa_backup_codes:
            user.mfa_backup_codes.remove(code)
            return True
        return False

    def enable_mfa(self, user: User, secret: str = None) -> str:
        if not secret:
            secret = self.generate_secret()
        user.mfa_secret = secret
        user.mfa_enabled = True
        user.mfa_backup_codes = self.generate_backup_codes(10)
        return secret

    def disable_mfa(self, user: User):
        user.mfa_enabled = False
        user.mfa_secret = ""
        user.mfa_backup_codes = []


class SessionManager:
    def __init__(self, db_path: str = "~/.erin/sessions.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                is_active INTEGER DEFAULT 1,
                mfa_verified INTEGER DEFAULT 0,
                permissions TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)")
        conn.commit()
        conn.close()

    def create_session(
        self,
        user_id: str,
        ip_address: str = "",
        user_agent: str = "",
        duration: timedelta = timedelta(hours=24),
        permissions: Set[Permission] = None,
        mfa_verified: bool = False,
        metadata: dict = None
    ) -> Session:
        session = Session(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + duration,
            permissions=permissions or set(),
            mfa_verified=mfa_verified,
            metadata=metadata or {},
        )

        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                INSERT INTO sessions (
                    session_id, user_id, created_at, expires_at, last_activity,
                    ip_address, user_agent, is_active, mfa_verified, permissions, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id, session.user_id, session.created_at.isoformat(),
                session.expires_at.isoformat(), session.last_activity.isoformat(),
                session.ip_address, session.user_agent, int(session.is_active),
                int(session.mfa_verified),
                json.dumps([p.value for p in session.permissions]),
                json.dumps(session.metadata)
            ))
            conn.commit()
            conn.close()

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return Session(
                session_id=row["session_id"],
                user_id=row["user_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"]),
                last_activity=datetime.fromisoformat(row["last_activity"]),
                ip_address=row["ip_address"],
                user_agent=row["user_agent"],
                is_active=bool(row["is_active"]),
                mfa_verified=bool(row["mfa_verified"]),
                permissions=set(Permission(p) for p in json.loads(row["permissions"])) if row["permissions"] else set(),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )

    def update_activity(self, session_id: str) -> bool:
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute(
                "UPDATE sessions SET last_activity = ? WHERE session_id = ? AND is_active = 1 AND expires_at > ?",
                (datetime.utcnow().isoformat(), session_id, datetime.utcnow().isoformat())
            )
            conn.commit()
            updated = cursor.rowcount > 0
            conn.close()
            return updated

    def extend_session(self, session_id: str, duration: timedelta = timedelta(hours=24)) -> bool:
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute(
                "UPDATE sessions SET expires_at = ? WHERE session_id = ? AND is_active = 1",
                ((datetime.utcnow() + timedelta(hours=24)).isoformat(), session_id)
            )
            conn.commit()
            updated = cursor.rowcount > 0
            conn.close()
            return updated

    def invalidate_session(self, session_id: str) -> bool:
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute("UPDATE sessions SET is_active = 0 WHERE session_id = ?", (session_id,))
            conn.commit()
            updated = cursor.rowcount > 0
            conn.close()
            return updated

    def invalidate_user_sessions(self, user_id: str, except_session: str = None) -> int:
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            if except_session:
                cursor = conn.execute("UPDATE sessions SET is_active = 0 WHERE user_id = ? AND session_id != ?", (user_id, except_session))
            else:
                cursor = conn.execute("UPDATE sessions SET is_active = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
            count = cursor.rowcount
            conn.close()
            return count

    def cleanup_expired(self) -> int:
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute("DELETE FROM sessions WHERE expires_at < ? OR is_active = 0", (datetime.utcnow().isoformat(),))
            conn.commit()
            count = cursor.rowcount
            conn.close()
            return count


class UserManager:
    def __init__(
        self,
        db_path: str = "~/.erin/users.db",
        password_policy: PasswordPolicy = None,
        mfa_manager: MFAManager = None,
        session_manager: SessionManager = None,
        audit_logger = None
    ):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.password_policy = password_policy or PasswordPolicy()
        self.mfa_manager = mfa_manager or MFAManager()
        self.session_manager = session_manager or SessionManager()
        self.audit_logger = audit_logger
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                email_verified INTEGER DEFAULT 0,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                status TEXT NOT NULL,
                roles TEXT NOT NULL,
                mfa_enabled INTEGER DEFAULT 0,
                mfa_secret TEXT,
                mfa_backup_codes TEXT,
                last_login TEXT,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TEXT,
                password_changed_at TEXT,
                last_password_change TEXT,
                api_keys TEXT,
                permissions TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_password_change TEXT,
                password_history TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
        conn.commit()
        conn.close()

    def _hash_password(self, password: str, salt: str = None) -> tuple:
        if salt is None:
            salt = secrets.token_hex(16)
        hash_val = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_val.hex(), salt

    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        computed_hash, _ = self._hash_password(password, salt)
        return hmac.compare_digest(computed_hash, password_hash)

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: List[str] = None,
        send_verification: bool = True
    ) -> User:
        if not username or not email or not password:
            raise ValueError("Username, email, and password are required")

        if self.get_user_by_email(email):
            raise ValueError("Email already registered")
        if self.get_user_by_username(username):
            raise ValueError("Username already taken")

        valid, errors = self.password_policy.validate(password)
        if not valid:
            raise ValueError(f"Password policy violation: {', '.join(errors)}")

        password_hash, salt = self._hash_password(password)

        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
            status=UserStatus.PENDING_VERIFICATION if not send_verification else UserStatus.ACTIVE,
            roles=roles or ["viewer"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                INSERT INTO users (
                    user_id, username, email, email_verified, password_hash, salt,
                    status, roles, mfa_enabled, mfa_secret, mfa_backup_codes,
                    last_login, failed_login_attempts, locked_until,
                    password_changed_at, last_password_change,
                    api_keys, permissions, metadata,
                    created_at, updated_at, last_password_change, password_history
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.user_id, user.username, user.email, int(user.email_verified),
                user.password_hash, user.salt, user.status.value,
                json.dumps(user.roles), int(user.mfa_enabled), user.mfa_secret,
                json.dumps(user.mfa_backup_codes), user.last_login.isoformat() if user.last_login else None,
                user.failed_login_attempts, user.locked_until.isoformat() if user.locked_until else None,
                user.password_changed_at.isoformat() if user.password_changed_at else None,
                user.last_password_change.isoformat() if user.last_password_change else None,
                json.dumps(user.api_keys), json.dumps([p.value for p in user.permissions]),
                json.dumps(user.metadata), user.created_at.isoformat(), user.updated_at.isoformat(),
                user.last_password_change.isoformat() if user.last_password_change else None,
                json.dumps(user.password_history)
            ))
            conn.commit()
            conn.close()

        if self.audit_logger:
            audit_log(
                AuditEventType.USER_CREATED, user_id=user.user_id,
                action="user_created", resource_type="user", resource_id=user.user_id,
                new_values={"username": username, "email": email, "roles": user.roles},
                risk_level="LOW"
            )

        return user

    def get_user(self, user_id: str) -> Optional[User]:
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            return self._row_to_user(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            conn.close()
            return self._row_to_user(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[User]:
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            conn.close()
            return self._row_to_user(row) if row else None

    def _row_to_user(self, row: sqlite3.Row) -> Optional[User]:
        if not row:
            return None
        return User(
            user_id=row["user_id"],
            username=row["username"],
            email=row["email"],
            email_verified=bool(row["email_verified"]),
            password_hash=row["password_hash"],
            salt=row["salt"],
            status=UserStatus(row["status"]),
            roles=json.loads(row["roles"]),
            mfa_enabled=bool(row["mfa_enabled"]),
            mfa_secret=row["mfa_secret"],
            mfa_backup_codes=json.loads(row["mfa_backup_codes"]) if row["mfa_backup_codes"] else [],
            last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None,
            failed_login_attempts=row["failed_login_attempts"],
            locked_until=datetime.fromisoformat(row["locked_until"]) if row["locked_until"] else None,
            password_changed_at=datetime.fromisoformat(row["password_changed_at"]) if row["password_changed_at"] else None,
            last_password_change=datetime.fromisoformat(row["last_password_change"]) if row["last_password_change"] else None,
            api_keys=json.loads(row["api_keys"]) if row["api_keys"] else [],
            permissions=set(Permission(p) for p in json.loads(row["permissions"])) if row["permissions"] else set(),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            password_history=json.loads(row["password_history"]) if row["password_history"] else [],
        )

    def authenticate(
        self,
        username_or_email: str,
        password: str,
        ip_address: str = "",
        user_agent: str = "",
        mfa_code: str = None
    ) -> tuple:
        user = self.get_user_by_email(username_or_email) or self.get_user_by_username(username_or_email)
        if not user:
            if self.audit_logger:
                audit_log(AuditEventType.USER_FAILED_LOGIN, user_id="unknown",
                         action="login_failed", ip_address=ip_address, user_agent=user_agent,
                         metadata={"reason": "user_not_found"}, risk_level="LOW")
            return None, "Invalid credentials"

        if user.status != UserStatus.ACTIVE:
            if self.audit_logger:
                audit_log(AuditEventType.USER_FAILED_LOGIN, user_id=user.user_id,
                         action="login_failed", ip_address=ip_address, user_agent=user_agent,
                         metadata={"reason": f"account_{user.status.value.lower()}"}, risk_level="MEDIUM")
            return None, f"Account is {user.status.value.lower()}"

        if user.is_locked():
            if self.audit_logger:
                audit_log(AuditEventType.USER_FAILED_LOGIN, user_id=user.user_id,
                         action="login_failed", ip_address=ip_address, user_agent=user_agent,
                         metadata={"reason": "account_locked"}, risk_level="MEDIUM")
            return None, "Account temporarily locked"

        if not self._verify_password(password, user.password_hash, user.salt):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= self.password_policy.lockout_threshold:
                user.locked_until = datetime.utcnow() + timedelta(minutes=self.password_policy.lockout_duration_minutes)
                if self.audit_logger:
                    audit_log(AuditEventType.USER_FAILED_LOGIN, user_id=user.user_id,
                             action="login_failed", ip_address=ip_address, user_agent=user_agent,
                             metadata={"reason": "lockout_threshold_reached"}, risk_level="HIGH")
            else:
                if self.audit_logger:
                    audit_log(AuditEventType.USER_FAILED_LOGIN, user_id=user.user_id,
                             action="login_failed", ip_address=ip_address, user_agent=user_agent,
                             metadata={"reason": "invalid_password"}, risk_level="LOW")
            self._update_user(user)
            return None, "Invalid credentials"

        if user.mfa_enabled:
            if not mfa_code:
                return None, "MFA_REQUIRED"
            if not self.mfa_manager.verify_totp(user.mfa_secret, mfa_code):
                if not self.mfa_manager.verify_backup_code(user, mfa_code):
                    if self.audit_logger:
                        audit_log(AuditEventType.USER_FAILED_LOGIN, user_id=user.user_id,
                                 action="login_failed", ip_address=ip_address, user_agent=user_agent,
                                 metadata={"reason": "invalid_mfa"}, risk_level="MEDIUM")
                    return None, "Invalid MFA code"

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        self._update_user(user)

        session = self.session_manager.create_session(
            user_id=user.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            mfa_verified=bool(mfa_code),
            permissions=user.get_all_permissions()
        )

        if self.audit_logger:
            audit_log(AuditEventType.USER_LOGIN, user_id=user.user_id,
                     session_id=session.session_id, action="login",
                     ip_address=ip_address, user_agent=user_agent,
                     metadata={"mfa_verified": bool(mfa_code)}, risk_level="LOW")

        return user, session

    def _update_user(self, user: User):
        user.updated_at = datetime.utcnow()
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                UPDATE users SET
                    email_verified=?, password_hash=?, salt=?, status=?,
                    roles=?, mfa_enabled=?, mfa_secret=?, mfa_backup_codes=?,
                    last_login=?, failed_login_attempts=?, locked_until=?,
                    password_changed_at=?, last_password_change=?,
                    api_keys=?, permissions=?, metadata=?,
                    updated_at=?, last_password_change=?, password_history=?
                WHERE user_id=?
            """, (
                int(user.email_verified), user.password_hash, user.salt, user.status.value,
                json.dumps(user.roles), int(user.mfa_enabled), user.mfa_secret,
                json.dumps(user.mfa_backup_codes), user.last_login.isoformat() if user.last_login else None,
                user.failed_login_attempts, user.locked_until.isoformat() if user.locked_until else None,
                user.password_changed_at.isoformat() if user.password_changed_at else None,
                user.last_password_change.isoformat() if user.last_password_change else None,
                json.dumps(user.api_keys), json.dumps([p.value for p in user.permissions]),
                json.dumps(user.metadata), datetime.utcnow().isoformat(),
                user.last_password_change.isoformat() if user.last_password_change else None,
                json.dumps(user.password_history), user.user_id
            ))
            conn.commit()
            conn.close()

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        if not self._verify_password(old_password, user.password_hash, user.salt):
            return False
        valid, errors = self.password_policy.validate(new_password, user)
        if not valid:
            raise ValueError(f"Password policy violation: {', '.join(errors)}")
        if new_hash in user.password_history:
            raise ValueError("Password cannot be reused")
        new_hash, new_salt = self._hash_password(new_password)
        user.password_hash = new_hash
        user.salt = new_salt
        user.password_changed_at = datetime.utcnow()
        user.last_password_change = datetime.utcnow()
        user.password_history.append(new_hash)
        user.password_history = user.password_history[-self.password_policy.history_length:]
        self._update_user(user)
        return True

    def reset_password(self, email: str, new_password: str) -> bool:
        user = self.get_user_by_email(email)
        if not user:
            return False
        valid, errors = self.password_policy.validate(new_password)
        if not valid:
            raise ValueError(f"Password policy violation: {', '.join(errors)}")
        new_hash, new_salt = self._hash_password(new_password)
        user.password_hash = new_hash
        user.salt = new_salt
        user.password_changed_at = datetime.utcnow()
        user.last_password_change = datetime.utcnow()
        user.password_history.append(new_hash)
        user.password_history = user.password_history[-self.password_policy.history_length:]
        self._update_user(user)
        return True

    def update_user(
        self,
        user_id: str,
        email: str = None,
        roles: List[str] = None,
        status: UserStatus = None,
        permissions: Set[Permission] = None,
        metadata: Dict = None
    ) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        old_values = user.to_dict(include_sensitive=True)
        if email is not None:
            existing = self.get_user_by_email(email)
            if existing and existing.user_id != user_id:
                raise ValueError("Email already in use")
            user.email = email
            user.email_verified = False
        if roles is not None:
            user.roles = roles
        if status is not None:
            user.status = status
        if permissions is not None:
            user.permissions = permissions
        if metadata is not None:
            user.metadata = metadata
        user.updated_at = datetime.utcnow()
        self._update_user(user)
        if self.audit_logger:
            audit_log(
                AuditEventType.USER_ROLE_CHANGE, user_id=user_id,
                action="user_updated", resource_type="user", resource_id=user_id,
                old_values=old_values, new_values=user.to_dict(),
                risk_level="MEDIUM"
            )
        return True

    def delete_user(self, user_id: str, deleted_by: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        self.session_manager.invalidate_user_sessions(user_id)
        user.status = UserStatus.DELETED
        user.updated_at = datetime.utcnow()
        self._update_user(user)
        if self.audit_logger:
            audit_log(
                AuditEventType.USER_DELETED, user_id=deleted_by,
                action="user_deleted", resource_type="user", resource_id=user_id,
                old_values=user.to_dict(include_sensitive=True),
                risk_level="HIGH"
            )
        return True

    def list_users(
        self,
        status: UserStatus = None,
        role: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        query = "SELECT * FROM users WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status.value)
        if role:
            query += " AND roles LIKE ?"
            params.append(f"%{role}%")
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
        return [self._row_to_user(row) for row in rows]


class RoleManager:
    def __init__(self, user_manager: UserManager):
        self.user_manager = user_manager

    def get_role_permissions(self, role: str) -> Set[Permission]:
        return DEFAULT_ROLES.get(role, set())

    def get_all_permissions(self) -> Dict[str, Set[Permission]]:
        return DEFAULT_ROLES.copy()

    def create_custom_role(
        self,
        name: str,
        permissions: Set[Permission],
        description: str = ""
    ) -> bool:
        if name in DEFAULT_ROLES:
            return False
        DEFAULT_ROLES[name] = permissions.copy()
        return True

    def delete_role(self, name: str) -> bool:
        if name in DEFAULT_ROLES and name not in ["super_admin", "admin", "viewer"]:
            del DEFAULT_ROLES[name]
            return True
        return False

    def get_users_with_role(self, role: str) -> List[User]:
        users = []
        for user_id in self.user_manager._get_all_user_ids():
            user = self.user_manager.get_user(user_id)
            if user and user.has_role(role):
                users.append(user)
        return users

    def assign_role(self, user_id: str, role: str) -> bool:
        return self.user_manager.get_user(user_id).add_role(role)

    def revoke_role(self, user_id: str, role: str) -> bool:
        return self.user_manager.get_user(user_id).remove_role(role)

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        user = self.user_manager.get_user(user_id)
        if not user:
            return set()
        return user.get_all_permissions()


class AccessControl:
    def __init__(self, role_manager: RoleManager):
        self.role_manager = role_manager

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        return permission in self.role_manager.get_user_permissions(user_id)

    def require_permission(self, user_id: str, permission: Permission):
        if not self.check_permission(user_id, permission):
            raise PermissionError(f"Missing required permission: {permission.value}")

    def check_resource_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str
    ) -> bool:
        action_perms = {
            "read": Permission.DATA_READ,
            "write": Permission.DATA_WRITE,
            "delete": Permission.DATA_WRITE,
            "export": Permission.DATA_EXPORT,
        }
        perm = action_perms.get(action.lower())
        if perm:
            return self.check_permission(user_id, perm)

        resource_perms = {
            "portfolio": {"read": Permission.PORTFOLIO_READ, "write": Permission.PORTFOLIO_WRITE},
            "order": {"read": Permission.TRADING_READ, "write": Permission.ORDER_PLACE},
            "risk": {"read": Permission.RISK_READ, "write": Permission.RISK_WRITE},
        }
        if resource_type in resource_perms and action.lower() in resource_perms[resource_type]:
            return self.check_permission(user_id, resource_perms[resource_type][action.lower()])
        return False


def create_password_policy(**kwargs) -> PasswordPolicy:
    return PasswordPolicy(**kwargs)


def create_mfa_manager(issuer: str = "ERIN") -> MFAManager:
    return MFAManager(issuer)


def create_session_manager(db_path: str = "~/.erin/sessions.db") -> SessionManager:
    return SessionManager(db_path)


def create_user_manager(
    db_path: str = "~/.erin/users.db",
    password_policy: PasswordPolicy = None,
    mfa_manager: MFAManager = None,
    session_manager: SessionManager = None,
    audit_logger = None
) -> UserManager:
    return UserManager(db_path, password_policy, mfa_manager, session_manager, audit_logger)


def create_role_manager(user_manager: UserManager) -> RoleManager:
    return RoleManager(user_manager)


def create_access_control(role_manager: RoleManager) -> AccessControl:
    return AccessControl(role_manager)