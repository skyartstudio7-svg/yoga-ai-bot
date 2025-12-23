"""
Onboarding conversation handler
Guides new users through initial setup and personalization
"""
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from database import SessionLocal, User
from ai import ClaudeClient
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

# Onboarding states
O_GOALS, O_EXPERIENCE, O_HEALTH, O_DURATION, O_REMINDER_FREQ, O_REMINDER_TIME, O_CONFIRMATION = range(7)


class OnboardingHandler:
    """Handles user onboarding flow"""
    
    def __init__(self):
        self.ai_client = ClaudeClient()
    
    async def restart_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Restart onboarding for existing users"""
        user = update.effective_user
        
        await update.message.reply_text(
            f"Добре, {user.first_name}! Давай оновимо твій профіль. 🔄\n\n"
            "Розкажи, що привело тебе до йоги? Що хотів би отримати від практики?\n\n"
            "Наприклад: зменшити стрес, покращити гнучкість, знайти внутрішній спокій..."
        )
        return O_GOALS
    
    async def start_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start onboarding conversation"""
        await update.message.reply_text(
            "Розкажи, що привело тебе до йоги? Що хотів би отримати від практики?\n\n"
            "Наприклад: зменшити стрес, покращити гнучкість, знайти внутрішній спокій..."
        )
        return O_GOALS
    
    async def collect_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Collect user goals"""
        user_message = update.message.text
        context.user_data['goals'] = user_message
        
        # Ask about experience (No AI response here as requested)
        keyboard = [
            ['Повний новачок 🌱'],
            ['Трохи практикував(ла) 🌿'],
            ['Є досвід 🌳']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "Який у тебе досвід з йогою?",
            reply_markup=reply_markup
        )
        return O_EXPERIENCE
    
    async def collect_experience(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Collect experience level"""
        experience_map = {
            'Повний новачок 🌱': 'beginner',
            'Трохи практикував(ла) 🌿': 'intermediate',
            'Є досвід 🌳': 'advanced'
        }
        
        experience = experience_map.get(update.message.text, 'beginner')
        context.user_data['experience_level'] = experience
        
        await update.message.reply_text(
            "Чудово! 👍\n\n"
            "Чи є якісь особливості здоров'я, про які мені варто знати? "
            "(біль у спині, проблеми з суглобами, тиск тощо)\n\n"
            "Якщо немає - просто напиши 'немає'",
            reply_markup=ReplyKeyboardRemove()
        )
        return O_HEALTH
    
    async def collect_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Collect health information"""
        health_info = update.message.text
        
        if health_info.lower() not in ['немає', 'ні', 'no']:
            context.user_data['health_conditions'] = [health_info]
        else:
            context.user_data['health_conditions'] = []
        
        # Ask about available duration
        keyboard = [
            ['10-15 хвилин'],
            ['20-30 хвилин'],
            ['45-60 хвилин']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "Скільки часу ти готовий(а) приділяти практиці?",
            reply_markup=reply_markup
        )
        return O_DURATION

    async def collect_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Collect available duration"""
        duration_map = {
            '10-15 хвилин': 15,
            '20-30 хвилин': 30,
            '45-60 хвилин': 60
        }
        
        duration = duration_map.get(update.message.text, 15)
        context.user_data['available_duration'] = duration
        
        # Ask about reminder frequency
        keyboard = [
            ['Щодня', 'Через день'],
            ['По буднях', 'По вихідних'],
            ['Вимкнути нагадування ❌']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "Як часто ти хочеш отримувати нагадування про практику? 🧘‍♂️",
            reply_markup=reply_markup
        )
        return O_REMINDER_FREQ

    async def collect_reminder_freq(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle frequency selection"""
        choice = update.message.text
        
        if choice == 'Вимкнути нагадування ❌':
            context.user_data['notifications_enabled'] = False
            context.user_data['reminder_frequency'] = 'off'
            context.user_data['reminder_time'] = None
            return await self.show_onboarding_summary(update, context)

        context.user_data['notifications_enabled'] = True
        context.user_data['reminder_frequency'] = choice
        
        await update.message.reply_text(
            "Введи час нагадування у форматі ГГ:ХХ (наприклад, 08:30 або 09:00):",
            reply_markup=ReplyKeyboardRemove()
        )
        return O_REMINDER_TIME

    async def collect_reminder_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle reminder time input"""
        time_text = update.message.text
        
        try:
            # Validate time format
            hour, minute = map(int, time_text.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
            
            context.user_data['reminder_time'] = f"{hour:02d}:{minute:02d}"
            return await self.show_onboarding_summary(update, context)
            
        except ValueError:
            await update.message.reply_text(
                "Будь ласка, введи час у правильному форматі ГГ:ХХ (наприклад, 08:30):"
            )
            return O_REMINDER_TIME

    async def show_onboarding_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show summary and confirm"""
        duration = context.user_data.get('available_duration', 15)
        freq = context.user_data.get('reminder_frequency', 'off')
        rem_time = context.user_data.get('reminder_time', '-')
        
        reminder_info = f"{freq} о {rem_time}" if freq != 'off' else "Вимкнено"
        
        summary = f"""
Чудово! Ось що я дізнався про тебе:

🎯 **Цілі:** {context.user_data.get('goals', 'N/A')}
📊 **Рівень:** {context.user_data.get('experience_level', 'N/A')}
⌛ **Тривалість:** {duration} хвилин
⏰ **Нагадування:** {reminder_info}

Тепер я зможу створювати персоналізовані практики саме для тебе! 🙏

Готовий(а) розпочати свою першу практику?
"""
        
        keyboard = [
            ['Так, почнімо! 🚀'],
            ['Змінити налаштування ⚙️']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
        return O_CONFIRMATION
    
    async def finish_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Finish onboarding and save user data"""
        user = update.effective_user
        
        if update.message.text == 'Змінити налаштування ⚙️':
            from bot import settings_command
            await settings_command(update, context)
            return ConversationHandler.END
        
        # Save user data to database
        with SessionLocal() as db:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if db_user:
                db_user.goals = context.user_data.get('goals', '')
                db_user.experience_level = context.user_data.get('experience_level', 'beginner')
                db_user.health_conditions = context.user_data.get('health_conditions', [])
                db_user.available_duration = context.user_data.get('available_duration', 15)
                db_user.reminder_frequency = context.user_data.get('reminder_frequency', 'off')
                db_user.reminder_time = context.user_data.get('reminder_time')
                db_user.notifications_enabled = context.user_data.get('notifications_enabled', True)
                db_user.current_state = 'active'
                db_user.last_active = datetime.utcnow()
                
                db.commit()
                
                # Schedule reminder if enabled
                if db_user.notifications_enabled and db_user.reminder_time:
                    try:
                        from handlers.reminders_handler import RemindersHandler
                        rem_handler = RemindersHandler()
                        hour, minute = map(int, db_user.reminder_time.split(':'))
                        rem_handler.schedule_user_reminder(
                            context.application if hasattr(context, 'application') else context, 
                            user.id, hour, minute, db_user.reminder_frequency
                        )
                    except Exception as e:
                        logger.error(f"Failed to schedule reminder during onboarding: {e}")
                
                logger.info(f"User {user.id} completed onboarding")
        
        keyboard = [
            ['Розпочати практику 🧘'],
            ['Переглянути прогрес 📊', 'Мій профіль 👤'],
            ['Налаштування ⚙️', 'Допомога 💡']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
        
        await update.message.reply_text(
            "Вітаю! Ти готовий(а) до практики! 🎉\n\n"
            "Використовуй /practice щоб розпочати свою першу практику.\n\n"
            "Намасте! 🙏",
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
    
    async def cancel_onboarding(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel onboarding"""
        await update.message.reply_text(
            "Онбординг скасовано. Використай /start щоб почати знову.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
