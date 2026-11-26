from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from app.db.database import Base

class AdminUserModel(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)  # "security_admin", "operator", "auditor"
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(Float, default=0.0)
    created_at = Column(String(30), nullable=False)

class SiteModel(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    domain = Column(String(255), nullable=False)
    site_key = Column(String(64), unique=True, index=True, nullable=False)
    secret_key_encrypted = Column(Text, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(String(30), nullable=False)

class SitePolicyModel(Base):
    __tablename__ = "site_policies"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(String(50), unique=True, index=True, nullable=False)
    mode = Column(String(20), default="challenge")
    policy_json = Column(Text, nullable=False)
    updated_at = Column(String(30), nullable=False)

class CryptoKeyModel(Base):
    __tablename__ = "crypto_keys"

    id = Column(Integer, primary_key=True, index=True)
    kid = Column(String(64), unique=True, index=True, nullable=False)
    algorithm = Column(String(20), default="EdDSA", nullable=False)
    curve = Column(String(20), default="Ed25519", nullable=False)
    public_key_pem = Column(Text, nullable=False)
    private_key_pem_encrypted = Column(Text, nullable=False)
    active = Column(Integer, default=1, index=True)  # 1 si es activa, 0 si fue rotada
    created_at = Column(String(30), nullable=False)

class ConsumedJTIModel(Base):
    __tablename__ = "consumed_jtis"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(64), unique=True, index=True, nullable=False)
    site_key = Column(String(64), index=True, nullable=False)
    expires_at = Column(Float, nullable=False)
    consumed_at = Column(String(30), nullable=False)

class ChallengeSessionModel(Base):
    __tablename__ = "challenge_sessions"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(String(64), unique=True, index=True, nullable=False)
    site_key = Column(String(64), index=True, nullable=False)
    target_route = Column(String(255), nullable=False)
    nonce = Column(String(64), nullable=False)
    difficulty = Column(Integer, default=3)
    expires_at = Column(Float, nullable=False)
    resolved = Column(Boolean, default=False)
    client_ip_hash = Column(String(64), nullable=False)
    interactive_type = Column(String(50), default="spatial_alignment")
    target_angle = Column(Integer, default=135)
    created_at = Column(String(30), nullable=False)

class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String(30), nullable=False)
    actor_username = Column(String(50), nullable=False)
    actor_role = Column(String(30), nullable=False)
    action = Column(String(50), nullable=False)
    resource = Column(String(255), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False, unique=True)

class SecurityEventModel(Base):
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    timestamp = Column(String(30), nullable=False)
    ip_hash = Column(String(64), index=True, nullable=False)
    route = Column(String(255), nullable=False)
    action = Column(String(30), nullable=False)  # "verified", "challenged", "blocked", "rate_limited"
    reason = Column(String(100), nullable=False)
    risk_score = Column(Float, nullable=False)
