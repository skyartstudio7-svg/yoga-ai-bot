"""
Profile management handler
Allows users to view and edit their profile
"""
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from database import SessionLocal, User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Profile states
PROFILE_MENU, EDIT_GOALS, EDIT_EXPERIENCE, EDIT_HEALTH, EDIT_DURATION = range(5)


class ProfileHandler:
    """Handles user profile viewing and editing"""
    
    async def show_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user profile with edit options"""
        user = update.effective_user
        
        with SessionLocal() as db:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await update.message.reply_text(
                    "Спочатку потрібно пройти онбординг. Використай /start"
                )
                return ConversationHandler.END
            
            # Format profile info
            experience_map = {
                'beginner': 'Повний новачок 🌱',
                'intermediate': 'Трохи практикував(ла) 🌿',
                'advanced': 'Є досвід 🌳'
            }
            
            time_map = {
                'morning': 'Ранок 🌅',
                'day': 'День ☀️',
                'evening': 'Вечір 🌙'
            }
            
            health_info = ', '.join(db_user.health_conditions) if db_user.health_conditions else 'Немає'
            
            profile_text = f"""
👤 **Твій профіль**

🎯 **Цілі:** {db_user.goals or 'Не вказано'}

📊 **Рівень досвіду:** {experience_map.get(db_user.experience_level, 'Не вказано')}

💊 **Особливості здоров'я:** {health_info}

⌛ **Тривалість практики:** {db_user.available_duration or 'Не вказано'} хвилин

Що хочеш змінити?
"""
            
            keyboard = [
                ['Цілі 🎯', 'Рівень досвіду 📊'],
                ['Здоров\'я 💊', 'Тривалість ⌛'],
                ['Готово ✅']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')
            return PROFILE_MENU
    
    async def handle_profile_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle profile menu selection"""
        choice = update.message.text
        
        if choice == 'Готово ✅':
            keyboard = [
                ['Розпочати практику 🧘'],
                ['Переглянути прогрес 📊', 'Мій профіль 👤'],
                ['Налаштування ⚙️', 'Допомога 💡']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
            await update.message.reply_text(
                "Профіль збережено! 👍",
                reply_markup=reply_markup
            )
            return ConversationHandler.END
        elif choice == 'Цілі 🎯':
            await update.message.reply_text(
                "Розкажи про свої нові цілі в йозі:",
                reply_markup=ReplyKeyboardRemove()
            )
            return EDIT_GOALS
        elif choice == 'Рівень досвіду 📊':
            keyboard = [
                ['Повний новачок 🌱'],
                ['Трохи практикував(ла) 🌿'],
                ['Є досвід 🌳']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Який у тебе рівень досвіду?",
                reply_markup=reply_markup
            )
            return EDIT_EXPERIENCE
        elif choice == 'Здоров\'я 💊':
            await update.message.reply_text(
                "Чи є якісь особливості здоров'я, про які мені варто знати?\n"
                "Якщо немає - напиши 'немає'",
                reply_markup=ReplyKeyboardRemove()
            )
            return EDIT_HEALTH
        elif choice == 'Тривалість ⌛':
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
            return EDIT_DURATION
        else:
            await update.message.reply_text("Будь ласка, обери опцію з меню")
            return PROFILE_MENU
    
    async def update_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update user goals"""
        user = update.effective_user
        new_goals = update.message.text
        
        with SessionLocal() as db:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if db_user:
                db_user.goals = new_goals
                db_user.last_active = datetime.utcnow()
                db.commit()
        
        await update.message.reply_text("Цілі оновлено! ✅")
        return await self.show_profile(update, context)
    
    async def update_experience(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update experience level"""
        user = update.effective_user
        
        experience_map = {
            'Повний новачок 🌱': 'beginner',
            'Трохи практикував(ла) 🌿': 'intermediate',
            'Є досвід 🌳': 'advanced'
        }
        
        experience = experience_map.get(update.message.text, 'beginner')
        
        with SessionLocal() as db:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if db_user:
                db_user.experience_level = experience
                db_user.last_active = datetime.utcnow()
                db.commit()
        
        await update.message.reply_text("Рівень досвіду оновлено! ✅")
        return await self.show_profile(update, context)
    
    async def update_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update health conditions"""
        user = update.effective_user
        health_info = update.message.text
        
        with SessionLocal() as db:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if db_user:
                if health_info.lower() not in ['немає', 'ні', 'no']:
                    db_user.health_conditions = [health_info]
                else:
                    db_user.health_conditions = []
                db_user.last_active = datetime.utcnow()
                db.commit()
        
        await update.message.reply_text("Інформацію про здоров'я оновлено! ✅")
        return await self.show_profile(update, context)
    
    async def update_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update available duration"""
        user = update.effective_user
        
        duration_map = {
            '10-15 хвилин': 15,
            '20-30 хвилин': 30,
            '45-60 хвилин': 60
        }
        
        duration = duration_map.get(update.message.text, 15)
        
        with SessionLocal() as db:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if db_user:
                db_user.available_duration = duration
                db_user.last_active = datetime.utcnow()
                db.commit()
        
        await update.message.reply_text("Тривалість практики оновлено! ✅")
        return await self.show_profile(update, context)
    
    async def cancel_profile_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel profile editing"""
        await update.message.reply_text(
            "Редагування профілю скасовано.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
