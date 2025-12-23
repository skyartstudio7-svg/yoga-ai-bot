"""
Practice session handlers
Manages practice creation, execution, and feedback
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from database import SessionLocal, User, Practice
from ai import ClaudeClient
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PracticeHandler:
    """Handles practice-related functionality"""
    
    def __init__(self):
        self.ai_client = ClaudeClient()
    
    async def start_practice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start a new practice session"""
        user = update.effective_user
        
        with SessionLocal() as db:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await update.message.reply_text(
                    "Спочатку потрібно пройти онбординг. Використай /start"
                )
                return
            
            # Check if user completed onboarding
            if not (db_user.goals and db_user.experience_level and db_user.available_duration):
                await update.message.reply_text(
                    "Спочатку давай завершимо знайомство! Використай /start"
                )
                return
            
            # Show practice type selection
            keyboard = [
                ['Асани (пози) 🧘'],
                ['Пранаяма (дихання) 🌬️'],
                ['Медитація 🧘‍♀️'],
                ['Комплексна практика ✨']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(
                "Який тип практики тебе цікавить сьогодні?",
                reply_markup=reply_markup
            )
            
            context.user_data['practice_flow'] = 'type_selection'
    
    async def handle_practice_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle practice type selection"""
        type_map = {
            'Асани (пози) 🧘': 'asana',
            'Пранаяма (дихання) 🌬️': 'pranayama',
            'Медитація 🧘‍♀️': 'meditation',
            'Комплексна практика ✨': 'complex'
        }
        
        if update.message.text not in type_map:
            # If it's not a valid type, skip processing.
            # We'll handle menu buttons in the main router.
            logger.info(f"Skipping practice generation for message: {update.message.text}")
            return
            
        practice_type = type_map[update.message.text]
        context.user_data['practice_type'] = practice_type
        
        # Clear flow so subsequent buttons work correctly
        context.user_data.pop('practice_flow', None)
        
        user = update.effective_user
        
        # Generate practice using AI
        await update.message.reply_text(
            "Створюю персоналізовану практику для тебе... ⏳"
        )
        
        with SessionLocal() as db:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            # Prepare user data for AI
            user_data = {
                'experience_level': db_user.experience_level,
                'goals': db_user.goals,
                'health_conditions': db_user.health_conditions or [],
                'available_duration': db_user.available_duration
            }
            
            # Generate practice
            try:
                import asyncio
                # Set a timeout for AI generation (e.g., 60 seconds)
                practice_content = await asyncio.wait_for(
                    self.ai_client.generate_practice(
                        user_data=user_data,
                        practice_type=practice_type,
                        duration=db_user.available_duration
                    ),
                    timeout=120.0
                )
                
                # Create practice record
                new_practice = Practice(
                    user_id=db_user.id,
                    practice_type=practice_type,
                    duration=db_user.available_duration,
                    practice_content=practice_content,
                    scheduled_at=datetime.utcnow(),
                    started_at=datetime.utcnow()
                )
                db.add(new_practice)
                db.commit()
                
                # Store practice ID for later
                context.user_data['current_practice_id'] = new_practice.id
                
                # Send practice to user
                practice_text = practice_content.get('content', 'Помилка генерації практики')
                
                await update.message.reply_text(
                    f"🧘 **Твоя персоналізована практика**\n\n{practice_text}",
                    parse_mode='Markdown'
                )
                
                # Ask for feedback after practice
                keyboard = [
                    ['Завершив(ла) практику ✅'],
                    ['Відкласти на потім ⏰']
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                
                await update.message.reply_text(
                    "Коли завершиш практику, дай мені знати!",
                    reply_markup=reply_markup
                )
                
            except asyncio.TimeoutError:
                logger.error("Timeout generating practice")
                await update.message.reply_text(
                    "Вибач, створення практики займає більше часу, ніж зазвичай. Спробуй ще раз пізніше або обери інший тип практики. ⏳"
                )
            except Exception as e:
                logger.error(f"Error generating practice: {e}", exc_info=True)
                await update.message.reply_text(
                    "Вибач, виникла помилка при створенні практики. Спробуй ще раз пізніше."
                )
    
    async def complete_practice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle practice completion - Step 1: Ask for rating"""
        if update.message.text == 'Відкласти на потім ⏰':
            keyboard = [
                ['Нагадати через годину ⏰'],
                ['Нагадати через 3 години ⏰']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Добре, практика збережена. Коли тобі нагадати? 🙏",
                reply_markup=reply_markup
            )
            context.user_data['practice_flow'] = 'reminder_setting'
            return
        
        practice_id = context.user_data.get('current_practice_id')
        
        with SessionLocal() as db:
            user = update.effective_user
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not practice_id and db_user:
                # Fallback: find latest uncompleted practice
                practice = db.query(Practice).filter(
                    Practice.user_id == db_user.id,
                    Practice.completed == False
                ).order_by(Practice.created_at.desc()).first()
                if practice:
                    practice_id = practice.id
                    context.user_data['current_practice_id'] = practice_id
            
            if not practice_id:
                await update.message.reply_text("Практика не знайдена. Спробуй створити нову за допомогою /practice")
                return

        # Ask for rating immediately
        keyboard = [
            ['⭐', '⭐⭐', '⭐⭐⭐'],
            ['⭐⭐⭐⭐', '⭐⭐⭐⭐⭐']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "Дякую за старанність! 🙏\nЯк ти почуваєшся після цієї практики?",
            reply_markup=reply_markup
        )
        
        context.user_data['practice_flow'] = 'rating'

    async def handle_reminder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle reminder setting"""
        choice = update.message.text
        hours = 1 if "годину" in choice else 3
        
        # Schedule reminder
        if context.job_queue:
            job_name = f"postponed_reminder_{update.effective_user.id}"
            
            # Remove any existing postponed reminders
            current_jobs = context.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()
            
            logger.info(f"Scheduling postponed reminder for user {update.effective_user.id} in {hours} hours")
            
            context.job_queue.run_once(
                self.send_reminder_job,
                when=timedelta(hours=hours),
                chat_id=update.effective_chat.id,
                user_id=update.effective_user.id,
                name=job_name
            )
            
            keyboard = [
                ['Розпочати практику 🧘'],
                ['Переглянути прогрес 📊', 'Мій профіль 👤'],
                ['Налаштування ⚙️', 'Допомога 💡']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
            
            await update.message.reply_text(
                f"Записав! Нагадаю тобі про практику через {hours} {'годину' if hours == 1 else 'години'}. 🧘‍♂️",
                reply_markup=reply_markup
            )
        else:
            logger.error("JobQueue not available in context")
            await update.message.reply_text("Вибач, не вдалося встановити нагадування. 😥")
            
        context.user_data.pop('practice_flow', None)

    async def send_reminder_job(self, context: ContextTypes.DEFAULT_TYPE):
        """Job to send reminder"""
        job = context.job
        logger.info(f"Triggering postponed reminder for chat {job.chat_id}")
        try:
            await context.bot.send_message(
                chat_id=job.chat_id,
                text="Привіт! Час для твоєї практики йоги. Почнемо? 🙏\n\nВикористовуй /practice щоб обрати заняття."
            )
        except Exception as e:
            logger.error(f"Error sending postponed reminder: {e}")
    
    async def handle_rating(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle practice rating and generate final summary"""
        rating_map = {
            '⭐': 1,
            '⭐⭐': 2,
            '⭐⭐⭐': 3,
            '⭐⭐⭐⭐': 4,
            '⭐⭐⭐⭐⭐': 5
        }
        
        rating = rating_map.get(update.message.text, 3)
        practice_id = context.user_data.get('current_practice_id')
        
        await update.message.reply_text(f"Дякую за відгук! {'🌟' * rating}\nГенерую підсумок твоєї практики... ⏳")
        
        with SessionLocal() as db:
            user = update.effective_user
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not practice_id and db_user:
                # Fallback: find latest uncompleted practice
                practice = db.query(Practice).filter(
                    Practice.user_id == db_user.id,
                    Practice.completed == False
                ).order_by(Practice.created_at.desc()).first()
                if practice:
                    practice_id = practice.id

            practice = db.query(Practice).filter(Practice.id == practice_id).first() if practice_id else None
            
            if practice:
                practice.completed = True
                practice.completed_at = datetime.utcnow()
                practice.rating = rating
                
                # Generate AI summary now
                practice_content_str = str(practice.practice_content.get('content', ''))
                try:
                    summary = await self.ai_client.generate_summary(practice_content_str)
                    if summary and len(summary.strip()) > 10:
                        practice.feedback = summary # Store summary in feedback field
                        
                        await update.message.reply_text(
                            f"📝 **Підсумок практики:**\n\n{summary}",
                            parse_mode='Markdown'
                        )
                except Exception as e:
                    logger.error(f"Error generating summary in handle_rating: {e}")
                
                db.commit()
        
        keyboard = [
            ['Розпочати практику 🧘'],
            ['Переглянути прогрес 📊', 'Мій профіль 👤'],
            ['Налаштування ⚙️', 'Допомога 💡']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Дякую за відгук! {'🌟' * rating}\n\n"
            "Чудова робота! Продовжуй практикувати регулярно. 🙏",
            reply_markup=reply_markup
        )
        
        # Clear practice flow
        context.user_data.pop('practice_flow', None)
        context.user_data.pop('current_practice_id', None)
