"""
Start and basic command handlers
"""
from telegram import Update
from telegram.ext import ContextTypes
from database import SessionLocal, User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = "Обери дію:"):
    """Show the main menu keyboard"""
    from telegram import ReplyKeyboardMarkup
    keyboard = [
        ['Розпочати практику 🧘'],
        ['Переглянути прогрес 📊', 'Мій профіль 👤'],
        ['Налаштування ⚙️', 'Допомога 💡']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=reply_markup)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command
    Creates new user or welcomes back existing user
    """
    from handlers.onboarding_handler import O_GOALS
    from telegram.ext import ConversationHandler

    try:
        print(f"DEBUG: Processing /start for user {update.effective_user.id}")
        user = update.effective_user
        
        def has_completed_onboarding(db_user):
            """Check if user has completed onboarding"""
            return (
                db_user.goals is not None and
                db_user.experience_level is not None and
                db_user.available_duration is not None
            )
        
        with SessionLocal() as db:
            # Check if user exists
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if db_user and has_completed_onboarding(db_user):
                # Existing user who completed onboarding
                db_user.last_active = datetime.utcnow()
                db.commit()
                
                await show_main_menu(update, context, f"Радий знову бачити тебе, {user.first_name}! 🙏")
                logger.info(f"Existing user {user.id} started bot")
                return ConversationHandler.END
            else:
                # New user or user who didn't complete onboarding
                if not db_user:
                    # Create new user
                    new_user = User(
                        telegram_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        current_state='onboarding_start'
                    )
                    db.add(new_user)
                    db.commit()
                    logger.info(f"New user {user.id} created")
                else:
                    # User exists but didn't complete onboarding
                    db_user.last_active = datetime.utcnow()
                    db_user.current_state = 'onboarding_start'
                    db.commit()
                    logger.info(f"User {user.id} restarting incomplete onboarding")
                
                welcome_message = f"""
✨ **Привіт, {user.first_name}!** 🙏

Ласкаво просимо до твого простору йоги та усвідомленості. Я — твій персональний AI-провідник, створений для того, щоб зробити твою практику гармонійною, регулярною та надихаючою.

**Чим я можу бути корисним:**
🌿 **Персоналізовані практики:** Створюю заняття під твій запит та стан.
🎯 **Гнучкість:** Ти обираєш час та тривалість (навіть 10 хв мають значення!).
📈 **Прогрес:** Відстежую твої досягнення та надихаю на нові кроки.
🧘 **Підтримка:** Я завжди поруч, щоб відповісти на твої питання про йогу.

Давай познайомимось ближче, щоб я міг підготувати для тебе щось особливе.

**Розкажи, що привело тебе до йоги?** Що б ти хотів(ла) змінити або відчути завдяки практиці? (Наприклад: спокій, гнучкість, енергію...)
"""
                await update.message.reply_text(welcome_message, parse_mode='Markdown')
                
                # Return O_GOALS state to start conversation
                return O_GOALS

    except Exception as e:
        logger.error(f"Error in start_command: {e}", exc_info=True)
        await update.message.reply_text("Вибач, сталася помилка. Спробуй ще раз пізніше.")
        return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🧘 **Доступні команди:**

/start - Почати спочатку
/onboarding - Пройти онбординг заново
/profile - Переглянути та редагувати профіль
/practice - Розпочати практику
/progress - Переглянути прогрес
/settings - Налаштування
/help - Ця довідка

📚 **Як це працює:**

1️⃣ Пройди коротке знайомство
2️⃣ Отримай персоналізовану практику
3️⃣ Практикуй регулярно
4️⃣ Відслідковуй прогрес
5️⃣ Поглиблюй знання

💡 **Потрібна допомога?**
Просто напиши мені своє питання!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')
