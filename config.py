"""
Configuration module for AI Yoga Telegram Bot
Loads environment variables and provides configuration settings
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Main configuration class"""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # OpenRouter API Configuration
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet')
    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///yoga_bot.db')
    
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Application Settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Bot Settings
    BOT_LANGUAGE = os.getenv('BOT_LANGUAGE', 'uk')
    TIMEZONE = os.getenv('TIMEZONE', 'Europe/Kyiv')
    
    # AI Settings
    MAX_TOKENS = 2000
    TEMPERATURE = 0.7
    
    # Practice Settings
    PRACTICE_REMINDER_TIME = "09:00"  # Default reminder time
    MIN_PRACTICE_DURATION = 5  # minutes
    MAX_PRACTICE_DURATION = 60  # minutes
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
        if not cls.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not set")
        return True


# Validate configuration on import
Config.validate()
