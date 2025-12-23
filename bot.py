"""
Main bot application
Initializes and runs the Telegram bot
"""
import logging
import pytz
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, filters, ContextTypes
from config import Config
from database import SessionLocal, User, Practice, init_db
from handlers import start_command, help_command, show_main_menu, OnboardingHandler, PracticeHandler, ProfileHandler, RemindersHandler
from handlers.onboarding_handler import O_GOALS, O_EXPERIENCE, O_HEALTH, O_DURATION, O_REMINDER_FREQ, O_REMINDER_TIME, O_CONFIRMATION
from handlers.profile_handler import PROFILE_MENU, EDIT_GOALS, EDIT_EXPERIENCE, EDIT_HEALTH, EDIT_DURATION
from handlers.reminders_handler import REMINDER_FREQ, REMINDER_TIME

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    """Handle /progress command with pagination"""
    user = update.effective_user
    is_callback = update.callback_query is not None
    
    # Timezone for Kyiv
    kyiv_tz = pytz.timezone('Europe/Kyiv')
    items_per_page = 5
    
    with SessionLocal() as db:
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        if not db_user:
            msg = "Спочатку пройди онбординг! 😊"
            if is_callback:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(msg)
            else:
                await update.message.reply_text(msg)
            return
            
        # Total count for pagination
        total_practices = db.query(Practice).filter(
            Practice.user_id == db_user.id,
            Practice.completed == True
        ).count()
        
        if total_practices == 0:
            msg = "У тебе ще немає завершених практик. Давай почнемо сьогодні! 🧘‍♂️"
            if is_callback:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(msg)
            else:
                await update.message.reply_text(msg)
            return
            
        total_pages = (total_practices + items_per_page - 1) // items_per_page
        if page > total_pages: page = total_pages
        if page < 1: page = 1
        
        # Get practices for current page
        offset = (page - 1) * items_per_page
        practices = db.query(Practice).filter(
            Practice.user_id == db_user.id,
            Practice.completed == True
        ).order_by(Practice.completed_at.desc()).offset(offset).limit(items_per_page).all()
        
        progress_text = f"📊 **Твій прогрес та підсумки (Сторінка {page}/{total_pages}):**\n\n"
        for p in practices:
            local_dt = p.completed_at.replace(tzinfo=pytz.utc).astimezone(kyiv_tz)
            date_str = local_dt.strftime("%d.%m %H:%M")
            
            emoji = "🧘" if p.practice_type == 'asana' else "🌬️" if p.practice_type == 'pranayama' else "🧘‍♀️"
            rating_stars = '⭐' * (p.rating or 0)
            progress_text += f"{emoji} **{date_str}** ({p.duration} хв) {rating_stars}\n"
            if p.feedback:
                progress_text += f"_{p.feedback}_\n"
            progress_text += "\n"
            
        # Inline buttons for pagination
        buttons = []
        if total_pages > 1:
            row = []
            if page > 1:
                row.append(InlineKeyboardButton("<< Назад", callback_data=f"prog_{page-1}"))
            if page < total_pages:
                row.append(InlineKeyboardButton("Вперед >>", callback_data=f"prog_{page+1}"))
            buttons.append(row)
            
        inline_markup = InlineKeyboardMarkup(buttons) if buttons else None
        
        # Main menu keyboard (ReplyKeyboardMarkup) to keep it visible
        main_keyboard = [
            ['Розпочати практику 🧘'],
            ['Мій профіль 👤', 'Налаштування ⚙️'],
            ['Допомога 💡', 'Назад 🔙']
        ]
        reply_markup = ReplyKeyboardMarkup(main_keyboard, one_time_keyboard=False, resize_keyboard=True)
        
        if is_callback:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                progress_text, 
                parse_mode='Markdown', 
                reply_markup=inline_markup
            )
        else:
            await update.message.reply_text(
                progress_text, 
                parse_mode='Markdown', 
                reply_markup=inline_markup
            )
            # Send/refresh the reply keyboard separately if needed, 
            # though PTB usually keeps the last reply keyboard. 
            # But here we want to ensure it's there.
            await update.message.reply_text("Скористайся меню нижче для навігації:", reply_markup=reply_markup)


async def settings_command(update, context):
    """Handle /settings command"""
    keyboard = [
        ['Профіль 👤', 'Нагадування ⏰'],
        ['Мова 🌐', 'Назад 🔙']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "⚙️ **Налаштування**\n\n"
        "Обери розділ, який хочеш змінити:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


def main():
    """Main function to run the bot"""
    logger.info("Initializing database...")
    init_db()
    
    onboarding_handler = OnboardingHandler()
    practice_handler = PracticeHandler()
    profile_handler = ProfileHandler()
    reminders_handler = RemindersHandler()

    async def post_init(application: Application):
        """Restore reminders from database on startup"""
        logger.info("Restoring reminders...")
        with SessionLocal() as db:
            users_with_reminders = db.query(User).filter(
                User.notifications_enabled == True,
                User.reminder_time != None,
                User.reminder_frequency != None
            ).all()
            
            for user in users_with_reminders:
                try:
                    hour, minute = map(int, user.reminder_time.split(':'))
                    reminders_handler.schedule_user_reminder(
                        application, user.telegram_id, hour, minute, user.reminder_frequency
                    )
                except Exception as e:
                    logger.error(f"Failed to restore reminder for user {user.telegram_id}: {e}")

    logger.info("Creating bot application...")
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()    
    
    async def exit_and_start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """End conversation and return to main menu"""
        await show_main_menu(update, context)
        return ConversationHandler.END

    async def exit_and_help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """End conversation and run help command"""
        await help_command(update, context)
        return ConversationHandler.END
        
    async def exit_and_practice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """End conversation and run practice handler"""
        await practice_handler.start_practice(update, context)
        return ConversationHandler.END

    async def exit_and_progress_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """End conversation and run progress command"""
        await progress_command(update, context)
        return ConversationHandler.END

    async def exit_and_settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """End conversation and run settings command"""
        await settings_command(update, context)
        return ConversationHandler.END
        
    async def exit_and_profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """End conversation and run profile handler"""
        await profile_handler.show_profile(update, context)
        return ConversationHandler.END

    async def exit_and_onboarding_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """End conversation and run onboarding handler"""
        await onboarding_handler.restart_onboarding(update, context)
        return ConversationHandler.END

    # Onboarding conversation handler
    onboarding_conv = ConversationHandler(
        entry_points=[
            CommandHandler('start', start_command),
            CommandHandler('onboarding', onboarding_handler.restart_onboarding),
            MessageHandler(filters.Regex('^Так, почнімо! 🚀$'), onboarding_handler.finish_onboarding),
        ],
        states={
            O_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_handler.collect_goals)],
            O_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_handler.collect_experience)],
            O_HEALTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_handler.collect_health)],
            O_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_handler.collect_duration)],
            O_REMINDER_FREQ: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_handler.collect_reminder_freq)],
            O_REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_handler.collect_reminder_time)],
            O_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_handler.finish_onboarding)],
        },
        fallbacks=[
            CommandHandler('cancel', onboarding_handler.cancel_onboarding),
            CommandHandler('start', exit_and_start_cmd),
            CommandHandler('help', exit_and_help_cmd),
            CommandHandler('practice', exit_and_practice_cmd),
            CommandHandler('progress', exit_and_progress_cmd),
            CommandHandler('settings', exit_and_settings_cmd),
            CommandHandler('profile', exit_and_profile_cmd),
            CommandHandler('onboarding', exit_and_onboarding_cmd),
        ],
        name="onboarding",
        persistent=False,
        allow_reentry=True
    )
    
    

    # Reminders conversation handler
    reminder_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^Нагадування ⏰$'), reminders_handler.start_reminder_settings)],
        states={
            REMINDER_FREQ: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminders_handler.handle_frequency)],
            REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminders_handler.handle_time)],
        },
        fallbacks=[
            CommandHandler('cancel', exit_and_settings_cmd),
            CommandHandler('start', exit_and_start_cmd),
            CommandHandler('help', exit_and_help_cmd),
        ],
        name="reminders",
        persistent=False,
        allow_reentry=True
    )

    # Profile conversation handler
    profile_conv = ConversationHandler(
        entry_points=[
            CommandHandler('profile', profile_handler.show_profile),
            MessageHandler(filters.Regex('^Мій профіль 👤$'), profile_handler.show_profile),
            MessageHandler(filters.Regex('^Профіль 👤$'), profile_handler.show_profile)
        ],
        states={
            PROFILE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_handler.handle_profile_menu)],
            EDIT_GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_handler.update_goals)],
            EDIT_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_handler.update_experience)],
            EDIT_HEALTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_handler.update_health)],
            EDIT_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_handler.update_duration)],
        },
        fallbacks=[
            CommandHandler('cancel', profile_handler.cancel_profile_edit),
            CommandHandler('start', exit_and_start_cmd),
            CommandHandler('help', exit_and_help_cmd),
            CommandHandler('practice', exit_and_practice_cmd),
            CommandHandler('progress', exit_and_progress_cmd),
            CommandHandler('settings', exit_and_settings_cmd),
            CommandHandler('profile', exit_and_profile_cmd),
            CommandHandler('onboarding', exit_and_onboarding_cmd),
        ],
        name="profile",
        persistent=False,
        allow_reentry=True
    )
    
    # Error handler
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a telegram message to notify the developer."""
        logger.error(msg="Exception while handling an update:", exc_info=context.error)
        
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "Вибач, сталася непередбачена помилка. 😥"
            )

    application.add_error_handler(error_handler)
    
    # Register handlers
    application.add_handler(onboarding_conv)  # Must be first to catch /start
    application.add_handler(profile_conv)
    application.add_handler(reminder_conv)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("practice", practice_handler.start_practice))
    application.add_handler(CommandHandler("progress", progress_command))
    application.add_handler(CommandHandler("settings", settings_command))
    
    # Progress pagination callback handler
    async def progress_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query.data.startswith('prog_'):
            page = int(query.data.split('_')[1])
            await progress_command(update, context, page=page)
            
    application.add_handler(CallbackQueryHandler(progress_callback_handler))
    
    # Message handler for practice flow and fallback
    async def handle_message(update, context):
        """Route messages based on current flow"""
        text = update.message.text
        
        # 1. Handle Global Navigation Buttons first
        if text == 'Назад 🔙':
            context.user_data.pop('practice_flow', None)
            await show_main_menu(update, context)
            return
        elif text == 'Налаштування ⚙️':
            context.user_data.pop('practice_flow', None)
            await settings_command(update, context)
            return
        elif text == 'Розпочати практику 🧘':
            context.user_data.pop('practice_flow', None)
            await practice_handler.start_practice(update, context)
            return
        elif text == 'Переглянути прогрес 📊':
            context.user_data.pop('practice_flow', None)
            await progress_command(update, context)
            return
        elif text == 'Допомога 💡':
            context.user_data.pop('practice_flow', None)
            await help_command(update, context)
            return
        elif text in ['Мій профіль 👤', 'Профіль 👤']:
            context.user_data.pop('practice_flow', None)
            await profile_handler.show_profile(update, context)
            return
        elif text == 'Нагадування ⏰':
            await reminders_handler.start_reminder_settings(update, context)
            return
        elif text == 'Мова 🌐':
            await update.message.reply_text("Ця функція незабаром з'явиться! 🚧")
            return
            
        # 2. Handle specific flows if no global button matched
        flow = context.user_data.get('practice_flow')
        if flow == 'type_selection':
            await practice_handler.handle_practice_type(update, context)
        elif flow == 'reminder_setting':
            await practice_handler.handle_reminder(update, context)
        elif flow == 'rating':
            await practice_handler.handle_rating(update, context)
        elif text in ['Завершив(ла) практику ✅', 'Відкласти на потім ⏰']:
            await practice_handler.complete_practice(update, context)
        elif text in ['Готово ✅', 'Так, почнімо! 🚀', 'Рівень досвіду 📊', 'Цілі 🎯', 'Здоров\'я 💊', 'Тривалість ⌛', 'Мій профіль 👤', 'Профіль 👤']:
            # These are handled by conversation handlers, 
            # but if they fall through, just show the main menu
            await show_main_menu(update, context)
        else:
            # 3. Fallback to AI Chat
            from ai import ClaudeClient
            ai_client = ClaudeClient()
            
            try:
                response = await ai_client.generate_general_response(
                    user_message=text,
                    user_data=context.user_data
                )
                await update.message.reply_text(response)
            except Exception as e:
                logger.error(f"Error generating AI response: {e}")
                await update.message.reply_text(
                    "Вибач, я не зовсім зрозумів. Спробуй використати команди:\n\n"
                    "/practice - Розпочати практику\n"
                    "/progress - Переглянути прогрес\n"
                    "/help - Допомога"
                )
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # application.post_init = post_init (Moved to builder)
    
    logger.info("Starting bot...")
    logger.info("Bot is ready! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
