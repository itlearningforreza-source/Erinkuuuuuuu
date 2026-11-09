import sys
sys.path.insert(0, 'packages/data-infra/src')
sys.path.insert(0, 'packages/market-intel/src')

from erin.market_intel.security import (
    AuditEventType, AuditEvent, AuditLogger, audit_log, get_audit_logger,
    KeyManager, KeyType, KeyStatus, EncryptedData,
    UserStatus, Permission, DEFAULT_ROLES, User, Session,
    PasswordPolicy, MFAManager, SessionManager, UserManager,
    RoleManager, AccessControl
)

print('Security module imports: OK')

# Test audit logging
audit = get_audit_logger()
event_id = audit.log_event(AuditEventType.USER_LOGIN, 'test_user', action='login_test')
print(f'Audit event logged: {event_id}')

# Test crypto
km = KeyManager()
key_id = km.generate_key(KeyType.DATA_ENCRYPTION)
encrypted = km.encrypt(b'Hello World', key_id)
decrypted = km.decrypt(encrypted)
print(f'Crypto: {decrypted.decode()}')

# Test auth
um = UserManager()
user = um.create_user('testuser', 'test@example.com', 'SecurePass123!')
session = um.authenticate('testuser', 'SecurePass123!', '127.0.0.1', 'TestAgent')
print(f'User created: {user.user_id}, Session: {session.session_id}')

# Test MFA
mfa = MFAManager()
secret = mfa.generate_secret()
qr = mfa.generate_qr_code('testuser', secret)
print(f'MFA secret generated: {secret[:8]}...')

print('Security module working!')