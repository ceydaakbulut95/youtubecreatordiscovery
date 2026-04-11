import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ENV: str = os.getenv("ENV", "dev")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./youtube_commenter.db")
    YOUTUBE_API_KEY: str | None = os.getenv("YOUTUBE_API_KEY")
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./youtube_commenter.db")
    
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "rule_based")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    FREE_SEARCH_LIMIT: int = int(os.getenv("FREE_SEARCH_LIMIT", "5"))
    PREMIUM_MONTHLY_PRICE_EUR: str = os.getenv("PREMIUM_MONTHLY_PRICE_EUR", "4.99")
    
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")
    PAYMENT_PRICE_EUR: str = os.getenv("PAYMENT_PRICE_EUR", "4.99")
    
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")
    
    MIN_DB_VIDEO_COMMENT_COUNT: int = int(os.getenv("MIN_DB_VIDEO_COMMENT_COUNT", "10"))
    
    ALLOWED_ORIGINS_RAW: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500",
    )

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]



settings = Settings()