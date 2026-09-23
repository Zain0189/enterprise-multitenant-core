from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    PROJECT_NAME: str = "Enterprise FDE Multi-Tenant Platform"
    ENVIRONMENT: str = "development"

    # Database URLs
    # ADMIN_DATABASE_URL: Used by Alembic for schema migrations (superuser)
    ADMIN_DATABASE_URL: str

    # APP_DATABASE_URL: Used by FastAPI at runtime (least privilege, enforces RLS)
    APP_DATABASE_URL: str

    # Load environment variables from the .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Instantiate a singleton configuration object
settings = Settings()
