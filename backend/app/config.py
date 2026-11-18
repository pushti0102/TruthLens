import os
from pathlib import Path
from dotenv import load_dotenv

# Load root .env file if available
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    PROJECT_NAME: str = "TruthLens"
    PROJECT_VERSION: str = "1.0.0"
    ENV: str = os.getenv("TRUTHLENS_ENV", "development")

    # Storage & Paths
    PROJECT_ROOT: Path = PROJECT_ROOT
    STORAGE_DIR: Path = PROJECT_ROOT / os.getenv("TRUTHLENS_STORAGE_DIR", "storage/verified_assets")
    SECRETS_DIR: Path = PROJECT_ROOT / "secrets"

    # Database
    DATABASE_URL: str = os.getenv("TRUTHLENS_DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/truthlens.db")

    # JWT Authentication
    JWT_SECRET_KEY: str = os.getenv("TRUTHLENS_JWT_SECRET", "truthlens_super_secure_jwt_secret_key_2026_dev_mode_only")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("TRUTHLENS_ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

    # Cryptography
    ACTIVE_KEY_ID: str = os.getenv("TRUTHLENS_ACTIVE_KEY_ID", "tl-key-ecdsa-2026-v1")
    ECDSA_PRIVATE_KEY_PATH: Path = PROJECT_ROOT / os.getenv(
        "TRUTHLENS_ECDSA_PRIVATE_KEY_PATH", "secrets/truthlens_signing_private.pem"
    )
    ECDSA_PRIVATE_KEY_PASSWORD: str = os.getenv("TRUTHLENS_ECDSA_PRIVATE_KEY_PASSWORD", "")
    ECDSA_PUBLIC_KEY_PATH: Path = PROJECT_ROOT / os.getenv(
        "TRUTHLENS_ECDSA_PUBLIC_KEY_PATH", "secrets/truthlens_signing_public.pem"
    )
    TRUSTED_KEYS_PATH: Path = PROJECT_ROOT / os.getenv(
        "TRUTHLENS_TRUSTED_KEYS_PATH", "secrets/trusted_keys_registry.json"
    )
    AES_KEY_ID: str = os.getenv("TRUTHLENS_AES_KEY_ID", "tl-aes-2026-v1")
    AES_MASTER_KEY_B64: str = os.getenv("TRUTHLENS_AES_MASTER_KEY_B64", "")

    # Upload validation
    MAX_UPLOAD_BYTES: int = int(os.getenv("TRUTHLENS_UPLOAD_MAX_BYTES", str(10 * 1024 * 1024)))
    MAX_UPLOAD_PIXELS: int = int(os.getenv("TRUTHLENS_UPLOAD_MAX_PIXELS", "25000000"))
    MAX_WIDTH: int = int(os.getenv("TRUTHLENS_UPLOAD_MAX_WIDTH", "8192"))
    MAX_HEIGHT: int = int(os.getenv("TRUTHLENS_UPLOAD_MAX_HEIGHT", "8192"))

    # Rate limiting
    RATE_LIMIT_DEFAULT: str = os.getenv("TRUTHLENS_RATE_LIMIT_DEFAULT", "60/minute")
    RATE_LIMIT_ANALYSIS: str = os.getenv("TRUTHLENS_RATE_LIMIT_ANALYSIS", "15/minute")

    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]


settings = Settings()
# Ensure directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.SECRETS_DIR.mkdir(parents=True, exist_ok=True)
