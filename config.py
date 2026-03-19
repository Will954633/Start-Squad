import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Telegram Bot Tokens
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    # Male team tokens
    PERSONA_TOKENS = {
        "damo": os.getenv("PERSONA_DAMO_TOKEN", ""),
        "sam": os.getenv("PERSONA_SAM_TOKEN", ""),
        "jake": os.getenv("PERSONA_JAKE_TOKEN", ""),
        "ryan": os.getenv("PERSONA_RYAN_TOKEN", ""),
        "tom": os.getenv("PERSONA_TOM_TOKEN", ""),
        # Female team tokens
        "tash": os.getenv("PERSONA_TASH_TOKEN", ""),
        "bree": os.getenv("PERSONA_BREE_TOKEN", ""),
        "priya": os.getenv("PERSONA_PRIYA_TOKEN", ""),
        "jess": os.getenv("PERSONA_JESS_TOKEN", ""),
        "mel": os.getenv("PERSONA_MEL_TOKEN", ""),
    }

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-nano-2026-03-17")

    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///start_squad.db"
    )

    # Admin
    ADMIN_TELEGRAM_IDS = [
        int(x.strip())
        for x in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",")
        if x.strip()
    ]

    # Sentry
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")

    # LLM Settings
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    MAX_MESSAGE_LENGTH = 280

    # Scheduler Settings
    DEFAULT_TIMEZONE = "Australia/Brisbane"

    @classmethod
    def is_production(cls) -> bool:
        return cls.ENVIRONMENT == "production"

    @classmethod
    def validate(cls) -> list[str]:
        """Return list of missing required config values."""
        errors = []
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required")
        return errors
