# Configuration and embeddings
"""
ClientIQ — Configuration Management
Centralizes all environment variable loading and validation using Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = Field(default="ClientIQ", env="APP_NAME")
    app_env: str = Field(default="development", env="APP_ENV")
    app_secret_key: str = Field(default="change-me", env="APP_SECRET_KEY")
    app_debug: bool = Field(default=True, env="APP_DEBUG")

    # ── TiDB ─────────────────────────────────────────────────────────────────
    tidb_host: str = Field(default="localhost", env="TIDB_HOST")
    tidb_port: int = Field(default=4000, env="TIDB_PORT")
    tidb_user: str = Field(default="root", env="TIDB_USER")
    tidb_password: str = Field(default="", env="TIDB_PASSWORD")
    tidb_database: str = Field(default="clientiq", env="TIDB_DATABASE")
    tidb_ssl: bool = Field(default=False, env="TIDB_SSL")

    # ── Pinecone ─────────────────────────────────────────────────────────────
    pinecone_api_key: str = Field(default="", env="PINECONE_API_KEY")
    pinecone_environment: str = Field(default="us-east-1-aws", env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="clientiq-docs", env="PINECONE_INDEX_NAME")

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: str = Field(default="mistral", env="LLM_PROVIDER")
    mistral_api_key: str = Field(default="", env="MISTRAL_API_KEY")
    mistral_base_url: str = Field(default="https://api.mistral.ai/v1", env="MISTRAL_BASE_URL")
    mistral_model: str = Field(default="mistral-small-latest", env="MISTRAL_MODEL")

    # ── Embeddings ───────────────────────────────────────────────────────────
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", env="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=384, env="EMBEDDING_DIMENSION")

    # ── JWT ──────────────────────────────────────────────────────────────────
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=480, env="JWT_EXPIRE_MINUTES")

    # ── RAG ──────────────────────────────────────────────────────────────────
    chunk_size: int = Field(default=512, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=64, env="CHUNK_OVERLAP")
    top_k_results: int = Field(default=5, env="TOP_K_RESULTS")

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/clientiq.log", env="LOG_FILE")

    @property
    def tidb_url(self) -> str:
        """Construct SQLAlchemy connection URL for TiDB (MySQL-compatible)."""
        return (
            f"mysql+pymysql://{self.tidb_user}:{self.tidb_password}"
            f"@{self.tidb_host}:{self.tidb_port}/{self.tidb_database}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached singleton settings instance."""
    return Settings()


# Module-level shortcut for convenience
settings = get_settings()
