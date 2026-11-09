"""Cryptography - Encryption, key management, and secure storage."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from enum import Enum
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
import base64

if TYPE_CHECKING:
    pass


class KeyType(str, Enum):
    """Types of cryptographic keys."""
    MASTER = "MASTER"           # Root key for key hierarchy
    DATA_ENCRYPTION = "DATA_ENCRYPTION"  # Data at rest encryption
    FIELD_ENCRYPTION = "FIELD_ENCRYPTION"  # Field-level encryption
    API_KEY = "API_KEY"         # API key encryption
    SESSION = "SESSION"         # Session token encryption
    BACKUP = "BACKUP"           # Backup encryption
    TRANSPORT = "TRANSPORT"     # TLS/transport encryption
    SIGNING = "SIGNING"         # Digital signatures
    VERIFICATION = "VERIFICATION"  # Signature verification


class KeyStatus(str, Enum):
    """Key lifecycle status."""
    ACTIVE = "ACTIVE"
    ROTATING = "ROTATING"
    DEPRECATED = "DEPRECATED"
    REVOKED = "REVOKED"
    DESTROYED = "DESTROYED"


@dataclass
class KeyMetadata:
    """Key metadata."""
    key_id: str
    key_type: KeyType
    algorithm: str = "AES-256-GCM"
    status: KeyStatus = KeyStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    rotated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    rotated_by: str = ""
    version: int = 1
    parent_key_id: Optional[str] = None
    usage_count: int = 0
    max_usage: int = 0  # 0 = unlimited
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EncryptedData:
    """Encrypted data with metadata."""
    ciphertext: bytes
    nonce: bytes
    tag: bytes
    key_id: str
    algorithm: str = "AES-256-GCM"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    associated_data: bytes = b""

    def to_dict(self) -> dict:
        return {
            "ciphertext": base64.b64encode(self.ciphertext).decode(),
            "nonce": base64.b64encode(self.nonce).decode(),
            "tag": base64.b64encode(self.tag).decode(),
            "key_id": self.key_id,
            "algorithm": self.algorithm,
            "timestamp": self.timestamp.isoformat(),
            "associated_data": base64.b64encode(self.associated_data).decode() if self.associated_data else "",
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'EncryptedData':
        return cls(
            ciphertext=base64.b64decode(data["ciphertext"]),
            nonce=base64.b64decode(data["nonce"]),
            tag=base64.b64decode(data["tag"]),
            key_id=data["key_id"],
            algorithm=data.get("algorithm", "AES-256-GCM"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            associated_data=base64.b64decode(data["associated_data"]) if data.get("associated_data") else b"",
        )


class KeyManager:
    """Hierarchical key management with rotation and access control."""

    def __init__(self, db_path: str = "~/.erin/keys.db", master_password: str = None):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._master_key: Optional[bytes] = None
        self._master_password = master_password
        self._keys: Dict[str, bytes] = {}  # key_id -> key material
        self._key_metadata: Dict[str, dict] = {}
        self._lock = threading.RLock()
        self._init_db()

        if master_password:
            self._derive_master_key(master_password)

    def _init_db(self):
        """Initialize key database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS keys (
                key_id TEXT PRIMARY KEY,
                key_type TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                status TEXT NOT NULL,
                encrypted_key BLOB NOT NULL,
                salt BLOB NOT NULL,
                nonce BLOB NOT NULL,
                tag BLOB NOT NULL,
                created_at TEXT NOT NULL,
                rotated_at TEXT,
                expires_at TEXT,
                rotated_by TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                parent_key_id TEXT,
                usage_count INTEGER DEFAULT 0,
                max_usage INTEGER DEFAULT 0,
                tags TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_keys_type_status ON keys(key_type, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_keys_parent ON keys(parent_key_id)")
        conn.commit()
        conn.close()

    def _derive_master_key(self, password: str):
        """Derive master key from password using PBKDF2."""
        salt = b"erin_master_salt"  # In production, use unique salt per installation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        self._master_key = kdf.derive(password.encode())

    def _encrypt_key(self, key: bytes) -> tuple:
        """Encrypt a key with master key."""
        if not self._master_key:
            raise ValueError("Master key not initialized")
        nonce = secrets.token_bytes(12)
        cipher = Cipher(algorithms.AES(self._master_key), modes.GCM(nonce))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(key) + encryptor.finalize()
        return ciphertext, nonce, encryptor.tag

    def _decrypt_key(self, ciphertext: bytes, nonce: bytes, tag: bytes) -> bytes:
        """Decrypt a key with master key."""
        if not self._master_key:
            raise ValueError("Master key not initialized")
        cipher = Cipher(algorithms.AES(self._master_key), modes.GCM(nonce, tag))
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    def generate_key(
        self,
        key_type: KeyType,
        algorithm: str = "AES-256-GCM",
        expires_in_days: int = None,
        parent_key_id: str = None,
        max_usage: int = 0,
        tags: Dict[str, str] = None,
        metadata: Dict = None,
        rotated_by: str = "system"
    ) -> str:
        """Generate a new encryption key."""
        key_id = f"key_{secrets.token_hex(16)}"
        key_material = secrets.token_bytes(32)  # 256-bit key

        # Encrypt key with master key
        ciphertext, nonce, tag = self._encrypt_key(key_material)

        metadata = metadata or {}
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                INSERT INTO keys (
                    key_id, key_type, algorithm, status, encrypted_key, salt, nonce, tag,
                    created_at, rotated_at, expires_at, rotated_by, version,
                    parent_key_id, usage_count, max_usage, tags, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key_id, key_type.value, algorithm, "ACTIVE",
                ciphertext, b"", nonce, tag,
                datetime.utcnow().isoformat(), None,
                expires_at.isoformat() if expires_at else None,
                rotated_by, 1,
                parent_key_id, 0, 0,
                json.dumps(tags or {}), json.dumps(metadata or {})
            ))
            conn.commit()
            conn.close()

            self._keys[key_id] = key_material
            self._key_metadata[key_id] = {
                "key_id": key_id,
                "key_type": key_type.value,
                "algorithm": algorithm,
                "status": "ACTIVE",
                "created_at": datetime.utcnow().isoformat(),
                "rotated_by": rotated_by,
                "version": 1,
                "parent_key_id": parent_key_id,
                "usage_count": 0,
                "max_usage": max_usage,
                "tags": tags or {},
                "metadata": metadata or {},
            }

        return key_id

    def get_key(self, key_id: str) -> Optional[bytes]:
        """Get decrypted key material."""
        with self._lock:
            if key_id in self._keys:
                self._key_metadata[key_id]["usage_count"] += 1
                return self._keys[key_id]

            # Load from database
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT encrypted_key, nonce, tag, algorithm FROM keys WHERE key_id = ? AND status = 'ACTIVE'",
                (key_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            key_material = self._decrypt_key(row["encrypted_key"], row["nonce"], row["tag"])
            self._keys[key_id] = key_material
            self._key_metadata[key_id] = dict(row)
            return key_material

    def encrypt(self, plaintext: Union[str, bytes], key_id: str, associated_data: bytes = b"") -> EncryptedData:
        """Encrypt data with a managed key."""
        key = self.get_key(key_id)
        if not key:
            raise ValueError(f"Key not found: {key_id}")

        if isinstance(plaintext, str):
            plaintext = plaintext.encode()

        nonce = secrets.token_bytes(12)
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
        encryptor = cipher.encryptor()

        if associated_data:
            encryptor.authenticate_additional_data(associated_data)

        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return EncryptedData(
            ciphertext=ciphertext,
            nonce=nonce,
            tag=encryptor.tag,
            key_id=key_id,
            timestamp=datetime.utcnow(),
            associated_data=associated_data
        )

    def decrypt(self, encrypted: EncryptedData, associated_data: bytes = b"") -> bytes:
        """Decrypt data with a managed key."""
        key = self.get_key(encrypted.key_id)
        if not key:
            raise ValueError(f"Key not found: {encrypted.key_id}")

        cipher = Cipher(algorithms.AES(key), modes.GCM(encrypted.nonce, encrypted.tag))
        decryptor = cipher.decryptor()

        if encrypted.associated_data:
            decryptor.authenticate_additional_data(encrypted.associated_data)
        elif associated_data:
            decryptor.authenticate_additional_data(associated_data)

        plaintext = decryptor.update(encrypted.ciphertext) + decryptor.finalize()
        return plaintext

    def rotate_key(self, key_id: str, rotated_by: str = "system") -> str:
        """Rotate an encryption key."""
        with self._lock:
            # Get old key metadata
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM keys WHERE key_id = ?", (key_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                raise ValueError(f"Key not found: {key_id}")

            # Generate new key
            new_key_id = self.generate_key(
                key_type=KeyType(row["key_type"]),
                algorithm=row["algorithm"],
                expires_in_days=None,
                parent_key_id=key_id,
                rotated_by=rotated_by,
            )

            # Mark old key as deprecated
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                "UPDATE keys SET status = 'DEPRECATED', rotated_at = ?, rotated_by = ? WHERE key_id = ?",
                (datetime.utcnow().isoformat(), rotated_by, key_id)
            )
            conn.commit()
            conn.close()

            # Update cache
            if key_id in self._keys:
                del self._keys[key_id]
            if key_id in self._key_metadata:
                self._key_metadata[key_id]["status"] = "DEPRECATED"
                self._key_metadata[key_id]["rotated_at"] = datetime.utcnow().isoformat()

            return new_key_id

    def revoke_key(self, key_id: str, revoked_by: str = "system") -> bool:
        """Revoke a key."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute("SELECT status FROM keys WHERE key_id = ?", (key_id,))
            row = cursor.fetchone()

            if not row or row[0] == "REVOKED" or row[0] == "DESTROYED":
                conn.close()
                return False

            conn.execute(
                "UPDATE keys SET status = 'REVOKED', rotated_at = ?, rotated_by = ? WHERE key_id = ?",
                (datetime.utcnow().isoformat(), revoked_by, key_id)
            )
            conn.commit()
            conn.close()

            if key_id in self._keys:
                del self._keys[key_id]
            if key_id in self._key_metadata:
                self._key_metadata[key_id]["status"] = "REVOKED"

            return True

    def list_keys(self, key_type: KeyType = None, status: str = None) -> List[Dict]:
        """List keys with optional filters."""
        query = "SELECT * FROM keys WHERE 1=1"
        params = []

        if key_type:
            query += " AND key_type = ?"
            params.append(key_type.value)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, [])
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_key_info(self, key_id: str) -> Optional[Dict]:
        """Get key metadata."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM keys WHERE key_id = ?", (key_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return dict(row)


class FieldEncryption:
    """Field-level encryption for database columns."""

    def __init__(self, key_manager: KeyManager, key_id: str):
        self.key_manager = key_manager
        self.key_id = key_id

    def encrypt(self, value: Any, associated_data: bytes = b"") -> str:
        """Encrypt a field value."""
        if value is None:
            return None

        if isinstance(value, (dict, list)):
            plaintext = json.dumps(value, sort_keys=True).encode()
        elif isinstance(value, (int, float)):
            plaintext = str(value).encode()
        elif isinstance(value, bool):
            plaintext = b"true" if value else b"false"
        elif isinstance(value, datetime):
            plaintext = value.isoformat().encode()
        elif isinstance(value, date):
            plaintext = value.isoformat().encode()
        elif isinstance(value, Decimal):
            plaintext = str(value).encode()
        elif isinstance(value, str):
            plaintext = value.encode()
        elif isinstance(value, bytes):
            plaintext = value
        else:
            plaintext = str(value).encode()

        encrypted = self.key_manager.encrypt(plaintext, self.key_id)
        return json.dumps(encrypted.to_dict())

    def decrypt(self, encrypted_json: str, expected_type: type = str) -> Any:
        """Decrypt a field value."""
        if not encrypted_json:
            return None

        encrypted_dict = json.loads(encrypted_json)
        encrypted = EncryptedData.from_dict(encrypted_dict)
        plaintext = self.key_manager.decrypt(encrypted)

        if expected_type == str:
            return plaintext.decode()
        elif expected_type == int:
            return int(plaintext.decode())
        elif expected_type == float:
            return float(plaintext.decode())
        elif expected_type == bool:
            return plaintext.decode().lower() == "true"
        elif expected_type == datetime:
            return datetime.fromisoformat(plaintext.decode())
        elif expected_type == date:
            return date.fromisoformat(plaintext.decode())
        elif expected_type == Decimal:
            return Decimal(plaintext.decode())
        elif expected_type in (dict, list):
            return json.loads(plaintext.decode())
        else:
            return plaintext.decode()


class SecureConfig:
    """Secure configuration storage with encryption."""

    def __init__(self, key_manager: KeyManager, config_key_id: str = "config_master"):
        self.key_manager = key_manager
        self.config_key_id = config_key_id
        self._cache: Dict[str, Any] = {}
        self._lock = threading.RLock()

        # Ensure config key exists
        if not self.key_manager.get_key(config_key_id):
            self.key_manager.generate_key(
                KeyType.FIELD_ENCRYPTION,
                key_id=config_key_id,
                expires_in_days=365,
            )

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        with self._lock:
            encrypted = self.key_manager.encrypt(json.dumps(value), self.config_key_id)
            self._cache[key] = encrypted.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        with self._lock:
            if key in self._cache:
                encrypted = EncryptedData.from_dict(self._cache[key])
                plaintext = self.key_manager.decrypt(encrypted)
                return json.loads(plaintext.decode())
            return default

    def delete(self, key: str) -> bool:
        """Delete a configuration value."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def list_keys(self) -> List[str]:
        """List all configuration keys."""
        with self._lock:
            return list(self._cache.keys())

    def export(self, key_id: str = None) -> str:
        """Export encrypted configuration."""
        with self._lock:
            export_key = key_id or self.config_key_id
            data = {
                "version": 1,
                "exported_at": datetime.utcnow().isoformat(),
                "config": self._cache,
            }
            encrypted = self.key_manager.encrypt(json.dumps(data), export_key)
            return json.dumps(encrypted.to_dict())

    def import_config(self, encrypted_json: str, key_id: str = None) -> bool:
        """Import encrypted configuration."""
        try:
            import_key = key_id or self.config_key_id
            encrypted = EncryptedData.from_dict(json.loads(encrypted_json))
            plaintext = self.key_manager.decrypt(encrypted, import_key)
            data = json.loads(plaintext)

            if data.get("version") != 1:
                raise ValueError("Unsupported config version")

            with self._lock:
                self._cache = data.get("config", {})
            return True
        except Exception as e:
            raise ValueError(f"Import failed: {e}")


class TokenManager:
    """Secure token generation and validation."""

    def __init__(self, key_manager: KeyManager, signing_key_id: str = "jwt_signing"):
        self.key_manager = key_manager
        self.signing_key_id = signing_key_id

        # Ensure signing key exists
        if not self.key_manager.get_key(signing_key_id):
            self.key_manager.generate_key(
                KeyType.SIGNING,
                algorithm="RS256",
                key_id=signing_key_id,
            )

    def create_token(self, payload: Dict[str, Any], expires_in: int = 3600) -> str:
        """Create a JWT-like token."""
        import jwt

        # Get private key for signing
        private_key_pem = self.key_manager.get_key(self.signing_key_id)
        if not private_key_pem:
            raise ValueError("Signing key not available")

        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None
        )

        payload = {
            **payload,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "jti": secrets.token_urlsafe(16),
        }

        return jwt.encode(payload, private_key, algorithm="RS256")

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode a token."""
        import jwt

        try:
            # Get public key
            private_key_pem = self.key_manager.get_key(self.signing_key_id)
            private_key = serialization.load_pem_private_key(
                private_key_pem, password=None
            )
            public_key = private_key.public_key()

            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_exp": True}
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def refresh_token(self, token: str, expires_in: int = 3600) -> Optional[str]:
        """Refresh an expired token."""
        payload = self.verify_token(token)
        if not payload:
            return None

        # Remove exp and iat, create new token
        payload.pop("exp", None)
        payload.pop("iat", None)
        payload.pop("jti", None)
        return self.create_token(payload, expires_in)


class SecureFileStorage:
    """Encrypted file storage with integrity verification."""

    def __init__(self, key_manager: KeyManager, storage_key_id: str = "file_storage", base_path: str = "~/.erin/files"):
        self.key_manager = key_manager
        self.storage_key_id = storage_key_id
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)

        if not key_manager.get_key(storage_key_id):
            key_manager.generate_key(
                KeyType.DATA_ENCRYPTION,
                key_id=storage_key_id,
            )

    def _get_file_path(self, file_id: str) -> Path:
        """Get file path from file ID."""
        # Use first 2 chars as subdirectory for better filesystem performance
        return self.base_path / file_id[:2] / file_id

    def store(self, file_id: str, data: bytes, metadata: Dict = None) -> Dict:
        """Store encrypted file."""
        file_path = self._get_file_path(file_id)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Encrypt data
        encrypted = self.key_manager.encrypt(data, self.storage_key_id)

        # Store encrypted data
        file_path.write_bytes(encrypted.ciphertext)

        # Store metadata
        meta = {
            "file_id": file_id,
            "original_size": len(data),
            "encrypted_size": len(encrypted.ciphertext),
            "algorithm": encrypted.algorithm,
            "key_id": encrypted.key_id,
            "nonce": base64.b64encode(encrypted.nonce).decode(),
            "tag": base64.b64encode(encrypted.tag).decode(),
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        meta_path = file_path.with_suffix(".meta.json")
        meta_path.write_text(json.dumps(meta, indent=2))

        return meta

    def retrieve(self, file_id: str) -> Optional[bytes]:
        """Retrieve and decrypt file."""
        file_path = self._get_file_path(file_id)
        meta_path = file_path.with_suffix(".meta.json")

        if not file_path.exists() or not meta_path.exists():
            return None

        # Read metadata
        meta = json.loads(meta_path.read_text())

        # Read encrypted data
        ciphertext = file_path.read_bytes()

        # Reconstruct encrypted data
        encrypted = EncryptedData(
            ciphertext=ciphertext,
            nonce=base64.b64decode(meta["nonce"]),
            tag=base64.b64decode(meta["tag"]),
            key_id=meta["key_id"],
            algorithm=meta["algorithm"],
        )

        # Decrypt
        return self.key_manager.decrypt(encrypted)

    def delete(self, file_id: str) -> bool:
        """Delete a file."""
        file_path = self._get_file_path(file_id)
        meta_path = file_path.with_suffix(".meta.json")

        deleted = False
        if file_path.exists():
            file_path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()
            deleted = True

        return deleted

    def list_files(self) -> List[Dict]:
        """List all stored files."""
        files = []
        for meta_path in self.base_path.rglob("*.meta.json"):
            try:
                meta = json.loads(meta_path.read_text())
                meta["meta_path"] = str(meta_path)
                files.append(meta)
            except Exception:
                pass
        return files


def create_key_manager(db_path: str = "~/.erin/keys.db", master_password: str = None) -> KeyManager:
    """Create a key manager."""
    return KeyManager(db_path, master_password)


def create_field_encryption(key_manager: KeyManager, key_id: str) -> FieldEncryption:
    """Create a field encryption helper."""
    return FieldEncryption(key_manager, key_id)


def create_secure_config(key_manager: KeyManager, config_key_id: str = "config_master") -> 'SecureConfig':
    """Create a secure configuration store."""
    return SecureConfig(key_manager, config_key_id)


def create_token_manager(key_manager: KeyManager, signing_key_id: str = "jwt_signing") -> TokenManager:
    """Create a token manager."""
    return TokenManager(key_manager, signing_key_id)


def create_file_storage(key_manager: KeyManager, storage_key_id: str = "file_storage", base_path: str = "~/.erin/files") -> SecureFileStorage:
    """Create encrypted file storage."""
    return SecureFileStorage(key_manager, storage_key_id, base_path)