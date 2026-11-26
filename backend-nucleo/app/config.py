import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    PROJECT_NAME: str = "Servicio Autónomo de Verificación Humana y Mitigación de Bots - Núcleo Backend"
    API_V1_STR: str = "/api/v1"
    
    # Base de datos
    DATABASE_PATH: str = str(BASE_DIR / "data" / "backend_nucleo.db")
    
    # Bóveda Criptográfica y Llave Maestra (AES-256-GCM)
    VAULT_MASTER_KEY: str = ""
    
    # Emisión de Tokens JWT Asimétricos
    JWT_ISSUER: str = "servicio-verificacion-humana.gob.ve"
    JWT_DEFAULT_TTL_SECONDS: int = 90
    JWT_MAX_TTL_SECONDS: int = 120
    
    # Retos y Prueba de Trabajo (PoW)
    CHALLENGE_TTL_SECONDS: int = 120
    POW_DIFFICULTY: int = 3
    
    # Conexión interna con IA Conductual (Dev 2)
    IA_SERVICE_URL: str = "http://ia-conductual:8001"
    IA_TIMEOUT_SECONDS: float = 0.5  # 500 ms circuit-breaker timeout
    
    # Autenticación Administrativa RBAC
    ADMIN_JWT_SECRET: str = ""
    ADMIN_JWT_EXPIRATION_MINUTES: int = 60
    
    # Sal rotativa diaria para anonimización de IP
    SALT_ROTATIVE_SECRET: str = ""

settings = Settings()

# Garantizar que el directorio de datos existe
db_dir = Path(settings.DATABASE_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)

# Inicializar llaves si no están en entorno
if not settings.VAULT_MASTER_KEY:
    key_file = db_dir / ".vault_master_key"
    if key_file.exists():
        settings.VAULT_MASTER_KEY = key_file.read_text().strip()
    else:
        new_key = secrets.token_hex(32)
        key_file.write_text(new_key)
        settings.VAULT_MASTER_KEY = new_key

if not settings.ADMIN_JWT_SECRET:
    admin_secret_file = db_dir / ".admin_jwt_secret"
    if admin_secret_file.exists():
        settings.ADMIN_JWT_SECRET = admin_secret_file.read_text().strip()
    else:
        new_secret = secrets.token_hex(32)
        admin_secret_file.write_text(new_secret)
        settings.ADMIN_JWT_SECRET = new_secret

if not settings.SALT_ROTATIVE_SECRET:
    settings.SALT_ROTATIVE_SECRET = secrets.token_hex(32)
