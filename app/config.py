from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str

    # Comma separated list of origins allowed to call this API from a browser.
    # Falls back to the usual local dev ports.
    cors_origins: str = ""

    @property
    def allowed_origins(self) -> list[str]:
        if self.cors_origins:
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
