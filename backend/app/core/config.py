from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL Configuration
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ila_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = Field(default="postgres")

    # Neo4j Configuration
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = Field(default="neo4j")

    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Risk Scoring Configuration
    RISK_ALERT_THRESHOLD: float = 6.5
    RISK_SCORE_WEIGHTS: dict[str, float] = {
        "anomaly_score": 0.30,
        "pattern_match_score": 0.25,
        "network_centrality": 0.20,
        "velocity_score": 0.15,
        "sentiment_score": 0.10,
    }
    SOURCE_RELIABILITY_MAP: dict[str, float] = {
        "HIGH": 1.2,
        "MEDIUM": 1.0,
        "LOW": 0.8,
    }

    # Security Configuration
    SECRET_KEY: str = Field(default="change-me-in-production-use-env-SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Evidence PDF storage (relative to CWD or absolute)
    EVIDENCE_STORAGE_DIR: str = Field(default="./data/evidence")
    PUBLIC_API_BASE: str = Field(default="http://localhost:8000")

    class Config:
        env_file = ".env"


settings = Settings()


def evidence_dir_path() -> Path:
    p = Path(settings.EVIDENCE_STORAGE_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p
