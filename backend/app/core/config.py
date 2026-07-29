from functools import lru_cache
from pathlib import Path
from typing import Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Rainbow Fashions Inventory"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    debug: bool = True

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rainbow_inventory"

    jwt_secret_key: str = Field(
        default="change-this-secret-before-production",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    upload_dir: Path = Path("app/uploads")
    invoice_upload_dir: Path = Path("app/uploads/invoices")
    product_upload_dir: Path = Path("app/uploads/products")
    max_upload_size_mb: int = 15
    max_product_image_size_mb: int = 5
    allowed_invoice_content_types: set[str] = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/heic",
        "image/heif",
        "application/pdf",
    }
    allowed_product_image_content_types: set[str] = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    ocr_provider: str = "local"
    max_invoice_pages: int = 20
    log_level: str = "INFO"
    delete_auth_password_hash: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, list[str]]) -> str:
        if isinstance(value, list):
            return ",".join(str(origin).strip() for origin in value if str(origin).strip())
        return value

    @field_validator("ocr_provider")
    @classmethod
    def validate_ocr_provider(cls, value: str) -> str:
        provider = value.strip().lower()
        if provider not in {"mock", "local", "tesseract"}:
            raise ValueError("OCR provider must be one of: mock, local, tesseract")
        return provider

    @field_validator("delete_auth_password_hash")
    @classmethod
    def validate_delete_auth_password_hash(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        password_hash = value.strip()
        if not password_hash.startswith("$argon2"):
            raise ValueError(
                "DELETE_AUTH_PASSWORD_HASH must contain a valid Argon2 hash, not a plain-text password."
            )
        return password_hash

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_product_image_size_bytes(self) -> int:
        return self.max_product_image_size_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
