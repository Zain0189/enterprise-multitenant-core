from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    PROJECT_NAME: str = "Enterprise FDE Multi-Tenant Platform"
    ENVIRONMENT: str = "development"

    # Database URLs
    ADMIN_DATABASE_URL: str
    APP_DATABASE_URL: str

    # Security & JWT Configuration
    JWT_SECRET_KEY: str = "enterprise_super_secret_signing_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Instantiate a singleton configuration object
settings = Settings()
