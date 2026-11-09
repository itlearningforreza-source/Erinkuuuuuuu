import sys
sys.path.insert(0, 'packages/data-infra/src')
sys.path.insert(0, 'packages/market-intel/src')

from erin.market_intel.security import (
    HardeningLevel, HardeningStatus, HardeningCheck, HardeningReport,
    HardeningEngine, SecurityHardening, SecureDefaults,
    SecurityConfigValidator, SecurityIncidentResponse,
    create_hardening_engine, create_security_hardening,
    create_secure_defaults, create_security_config_validator,
    create_security_incident_response
)

print('Security Hardening imports: OK')

engine = create_hardening_engine(HardeningLevel.STANDARD)
print(f'Hardening Engine: {len(engine.checks)} checks registered')

hardening = create_security_hardening(HardeningLevel.STANDARD)
print('Security Hardening created successfully')

defaults = create_secure_defaults()
print(f'Secure defaults: NGINX config length: {len(defaults.NGINX_SECURE_CONFIG)}')

validator = create_security_config_validator()
print('Config validator created successfully')

ir = create_security_incident_response()
playbook = ir.get_playbook('data_breach')
print(f'Incident response playbook: {playbook["name"]}')

print('Security Hardening module working!')