from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "GestureMed AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://gesturemed:gesturemed_secret@localhost:5432/gesturemed"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    AI_PROVIDER: str = "anthropic"  # anthropic | openai | gemini | ollama
    AI_MODEL: str = "claude-opus-4-20250514"

    # RAG (V2) - free/local only
    QDRANT_URL: str = "http://localhost:6333"
    OLLAMA_URL: str = "http://localhost:11434"
    RAG_ENABLE_PUBMED: bool = True
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # GPU / ROCm (V2)
    GPU_ENABLED: bool = True
    GPU_BACKEND: str = "auto"  # auto | rocm | cuda | cpu
    GPU_MEMORY_FRACTION: float = 0.9
    OLLAMA_FALLBACK_MODEL: str = "llama3"

    # CORS
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # File uploads
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB

    # Band of Agents Configuration
    BAND_ENABLED: bool = True
    BAND_API_KEY: str = ""
    BAND_ORG_ID: str = ""
    BAND_FALLBACK_MODE: bool = True  # Use LocalEventBus if Band unavailable
    AGENT_TIMEOUT_SECONDS: int = 30
    AGENT_MAX_RETRIES: int = 2
    
    # Demo Mode
    DEMO_MODE: bool = False  # Enables seeded consultation flow for judges
    DEMO_PATIENT_NAME: str = "John Doe"
    DEMO_CHIEF_COMPLAINT: str = "Shoulder Pain"
    DEMO_PAIN_SCORE: int = 4
    DEMO_MEDICAL_HISTORY: str = "Previous Shoulder Injury, Aspirin Allergy"
    DEMO_INSURANCE_PLAN: str = "Active PPO Plan"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()