from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # PostgreSQL Configuration
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ila_db"
    POSTGRES_USER: str = "ila_user"
    POSTGRES_PASSWORD: str  # Required - must be set via environment variable

    # Neo4j Configuration
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str  # Required - must be set via environment variable

    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Security Configuration
    SECRET_KEY: str  # Required - must be set via environment variable
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"

settings = Settings()