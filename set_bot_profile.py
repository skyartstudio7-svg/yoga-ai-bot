
import asyncio
import logging
from telegram import Bot
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def set_bot_profile():
    """Set bot's name, description and about text via Telegram API"""
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in config")
        return

    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    
    try:
        # 1. Set Bot Name
        name = "Yoga AI Assistant"
        # await bot.set_my_name(name=name) # Available in newer ptb versions
        
        # 2. Set Bot Description (Seen when someone opens the bot for the first time)
        description = (
            "Твій персональний AI-провідник у світі йоги. 🧘\n\n"
            "Допомагаю створювати індивідуальні практики, відстежувати прогрес та "
            "знаходити гармонію кожного дня. Натисни /start, щоб почати подорож! ✨"
        )
        await bot.set_my_description(description=description)
        logger.info("Bot description updated successfully")

        # 3. Set Bot Short Description (Seen on the bot's profile page / 'About' section)
        short_description = "AI Yoga Coach: персональні практики, прогрес та гармонія. 🌿"
        await bot.set_my_short_description(short_description=short_description)
        logger.info("Bot short description updated successfully")
        
        print("BOT PROFILE UPDATED SUCCESSFULLY")
        
    except Exception as e:
        logger.error(f"Error updating bot profile: {e}")

if __name__ == "__main__":
    asyncio.run(set_bot_profile())
