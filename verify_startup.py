
import logging
from config import Config
from database import init_db
from telegram.ext import Application
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_startup():
    try:
        logger.info("Checking configuration...")
        Config.validate()
        logger.info("Configuration valid.")

        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized.")

        logger.info("Checking Telegram Bot Token...")
        if not Config.TELEGRAM_BOT_TOKEN:
             raise ValueError("Bot token missing")
        
        # Just build the app to check for immediate errors, don't run it
        app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        logger.info("Application built successfully.")
        
        print("VERIFICATION SUCCESSFUL")
        return 0
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(verify_startup())
