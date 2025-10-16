from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    PUBLIC_INTERFACE
    Application settings loaded from environment variables.
    """
    APP_NAME: str = "Wiki to Neo4j Extraction API"
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 3001

    # JWT
    JWT_SECRET: str = Field(default="change-me", description="JWT secret for signing tokens")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    JWT_ISSUER: str = "wiki-backend"
    JWT_AUDIENCE: str = "wiki-clients"

    # Optional OpenAI
    OPENAI_API_KEY: str | None = None

    # Neo4j
    NEO4J_URI: str | None = None
    NEO4J_USER: str | None = None
    NEO4J_PASSWORD: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"
