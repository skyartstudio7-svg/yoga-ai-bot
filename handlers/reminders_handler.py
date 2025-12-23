"""
Reminders management handler
Allows users to set practice reminders
"""
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from database import SessionLocal, User
from datetime import datetime, time
import logging
import pytz

logger = logging.getLogger(__name__)

# Reminder states
REMINDER_FREQ, REMINDER_TIME = range(2)

class RemindersHandler:
    """Handles setting up practice reminders"""
    
    async def start_reminder_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start reminder setup flow"""
        keyboard = [
            ['Щодня', 'Через день'],
            ['По буднях', 'По вихідних'],
            ['Вимкнути нагадування ❌'],
            ['Назад 🔙']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "Як часто ти хочеш отримувати нагадування про практику? 🧘‍♂️",
            reply_markup=reply_markup
        )
        return REMINDER_FREQ

    async def handle_frequency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle frequency selection"""
        choice = update.message.text
        
        if choice == 'Назад 🔙':
            from bot import settings_command
            await settings_command(update, context)
            return ConversationHandler.END
            
        if choice == 'Вимкнути нагадування ❌':
            user = update.effective_user
            with SessionLocal() as db:
                db_user = db.query(User).filter(User.telegram_id == user.id).first()
                if db_user:
                    db_user.notifications_enabled = False
                    db.commit()
                    # Remove scheduled job
                    self.remove_user_reminder(context, user.id)
            
            keyboard = [
                ['Розпочати практику 🧘'],
                ['Переглянути прогрес 📊', 'Мій профіль 👤'],
                ['Допомога 💡']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
            await update.message.reply_text("Нагадування вимкнено. 🔇", reply_markup=reply_markup)
            return ConversationHandler.END

        # Store frequency in user_data
        context.user_data['temp_reminder_freq'] = choice
        
        await update.message.reply_text(
            "Введи час нагадування у форматі ГГ:ХХ (наприклад, 08:30 або 19:00):",
            reply_markup=ReplyKeyboardRemove()
        )
        return REMINDER_TIME

    async def handle_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle time input and finish setup"""
        time_text = update.message.text
        user = update.effective_user
        
        try:
            # Validate time format
            hour, minute = map(int, time_text.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
            
            freq = context.user_data.get('temp_reminder_freq')
            
            with SessionLocal() as db:
                db_user = db.query(User).filter(User.telegram_id == user.id).first()
                if db_user:
                    db_user.reminder_frequency = freq
                    db_user.reminder_time = f"{hour:02d}:{minute:02d}"
                    db_user.notifications_enabled = True
                    db.commit()
            
            # Schedule the job
            self.schedule_user_reminder(context, user.id, hour, minute, freq)
            
            keyboard = [
                ['Розпочати практику 🧘'],
                ['Переглянути прогрес 📊', 'Мій профіль 👤'],
                ['Допомога 💡']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
            
            await update.message.reply_text(
                f"Чудово! Я нагадуватиму тобі про практику: **{freq}** о **{hour:02d}:{minute:02d}**. 🙏",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text(
                "Будь ласка, введи час у правильному форматі ГГ:ХХ (наприклад, 09:00):"
            )
            return REMINDER_TIME

    def schedule_user_reminder(self, context, user_id, hour, minute, frequency):
        """Schedule a recurring message for the user"""
        job_name = f"reminder_{user_id}"
        
        # Determine job_queue (can be context or application)
        job_queue = context.job_queue if hasattr(context, 'job_queue') else context
        
        # Remove existing job if any
        self.remove_user_reminder(context, user_id)
        
        kyiv_tz = pytz.timezone('Europe/Kyiv')
        reminder_time = time(hour=hour, minute=minute, tzinfo=kyiv_tz)
        
        # Determine frequency logic
        if frequency == 'Щодня':
            job_queue.run_daily(self.send_reminder, reminder_time, chat_id=user_id, name=job_name)
        elif frequency == 'Через день':
            # run_repeating with interval of 2 days
            # We use first to set the clock time
            job_queue.run_repeating(self.send_reminder, interval=172800, first=reminder_time, chat_id=user_id, name=job_name)
        elif frequency == 'По буднях':
            job_queue.run_daily(self.send_reminder, reminder_time, days=(0, 1, 2, 3, 4), chat_id=user_id, name=job_name)
        elif frequency == 'По вихідних':
            job_queue.run_daily(self.send_reminder, reminder_time, days=(5, 6), chat_id=user_id, name=job_name)
        else:
            job_queue.run_daily(self.send_reminder, reminder_time, chat_id=user_id, name=job_name)

    def remove_user_reminder(self, context, user_id):
        """Remove existing reminder job"""
        job_name = f"reminder_{user_id}"
        job_queue = context.job_queue if hasattr(context, 'job_queue') else context
        current_jobs = job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()

    async def send_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        """Job callback to send the reminder"""
        job = context.job
        await context.bot.send_message(
            chat_id=job.chat_id,
            text="Привіт! Час для твоєї практики йоги. Твоє тіло та розум будуть вдячні! 🙏🧘‍♂️\n\nНатисни /practice, щоб почати."
        )
