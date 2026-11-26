from typing import Optional, List
from pydantic import BaseModel, Field

class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6, description="Código TOTP si el usuario tiene MFA habilitado")

class AdminLoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    mfa_required: bool = False
    temp_token: Optional[str] = None
    role: Optional[str] = None
    username: Optional[str] = None

class TOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_svg: Optional[str] = None

class TOTPVerifyRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=6)

class SiteCreateRequest(BaseModel):
    site_id: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=3, max_length=100)
    domain: str = Field(..., min_length=3, max_length=255)

class SiteResponse(BaseModel):
    site_id: str
    site_key: str
    name: str
    domain: str
    created_at: str
    active: bool

class RotateKeyResponse(BaseModel):
    kid: str
    algorithm: str = "EdDSA"
    curve: str = "Ed25519"
    created_at: str
    message: str

class ModelUploadResponse(BaseModel):
    model_version: str
    checksum_sha256: str
    message: str
    reloaded_in_ia: bool
