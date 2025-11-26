"""
Telegram bot module for handling user messages
"""
import logging
from typing import Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from app.config import Config
from app.openai_service import OpenAIService
from app.linkedin_service_http import LinkedInServiceHTTP as LinkedInService

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.info("Using HTTP-based LinkedIn service (direct API, no Node.js needed)")


class TelegramBot:
    """Telegram bot handler"""
    
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.openai_service = OpenAIService()
        self.linkedin_service = LinkedInService()
        self.application: Optional[Application] = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """👋 Привет! Я — LinkedIn Job Assistant.

Я умею:
📋 Показать ваш профиль LinkedIn
💼 Искать вакансии на LinkedIn

Примеры запросов:
• "Покажи мой профиль"
• "Найди вакансии Python разработчика"
• "Вакансии data scientist в Берлине"
• "Удалённая работа frontend developer"

Просто напишите мне, что вы хотите! 🚀"""
        
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """❓ Помощь

Доступные команды:
/start - Начать работу
/help - Показать эту помощь
/seturl <URL> - Установить LinkedIn профиль URL
/refresh - Обновить данные профиля

Что я умею:
1️⃣ Показать ваш профиль LinkedIn
   Примеры: "мой профиль", "покажи опыт работы"

2️⃣ Искать вакансии
   Примеры:
   • "найди вакансии Python developer"
   • "работа data scientist в Лондоне"
   • "удалённая работа для фронтенд разработчика"

Просто напишите свой запрос обычным языком! 💬"""
        
        await update.message.reply_text(help_message)
    
    async def refresh_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /refresh command to refresh LinkedIn profile data"""
        await update.message.reply_text("🔄 Обновляю данные профиля LinkedIn...")
        
        try:
            # Use HTTP service method
            result = self.linkedin_service.refresh_profile()
            
            if result.get("success"):
                await update.message.reply_text(
                    "✅ Профиль успешно обновлён!\n\n"
                    "Теперь попробуйте: 'Покажи мой профиль'"
                )
            else:
                error_msg = result.get("error", "Неизвестная ошибка")
                await update.message.reply_text(
                    f"❌ Не удалось обновить профиль: {error_msg}"
                )
        
        except Exception as e:
            logger.error(f"Error refreshing profile: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Ошибка при обновлении профиля. Попробуйте позже."
            )
    
    async def seturl_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /seturl command to set LinkedIn profile URL"""
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "❌ Укажите LinkedIn URL\n\n"
                "Использование: /seturl https://www.linkedin.com/in/your-profile\n\n"
                "Пример: /seturl https://www.linkedin.com/in/johnsmith"
            )
            return
        
        linkedin_url = context.args[0]
        
        # Validate URL format
        if not linkedin_url.startswith("https://www.linkedin.com/in/"):
            await update.message.reply_text(
                "❌ Неверный формат URL\n\n"
                "URL должен начинаться с: https://www.linkedin.com/in/\n\n"
                "Пример: https://www.linkedin.com/in/johnsmith"
            )
            return
        
        await update.message.reply_text(f"⏳ Устанавливаю LinkedIn URL: {linkedin_url}")
        
        try:
            # Use HTTP service method
            result = self.linkedin_service.set_linkedin_url(linkedin_url)
            
            if result.get("success"):
                await update.message.reply_text(
                    "✅ LinkedIn URL успешно установлен!\n\n"
                    "Теперь вы можете использовать:\n"
                    "• 'Покажи мой профиль'\n"
                    "• 'Найди вакансии'"
                )
            else:
                error_msg = result.get("error", "Неизвестная ошибка")
                await update.message.reply_text(
                    f"❌ Не удалось установить URL: {error_msg}"
                )
        
        except Exception as e:
            logger.error(f"Error setting LinkedIn URL: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Ошибка при установке LinkedIn URL. Попробуйте позже."
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user text messages"""
        user_message = update.message.text
        user_id = update.effective_user.id
        
        logger.info(f"Received message from {user_id}: {user_message}")
        
        # Send "typing" status
        await update.message.chat.send_action("typing")
        
        try:
            # Step 1: Classify intent using OpenAI
            intent_result = self.openai_service.classify_intent(user_message)
            logger.info(f"Classified intent: {intent_result.intent} (confidence: {intent_result.confidence})")
            
            # Step 2: Process based on intent
            if intent_result.intent == "PROFILE":
                await self._handle_profile_request(update)
            
            elif intent_result.intent == "JOBS":
                await self._handle_jobs_request(update, intent_result)
            
            else:  # UNKNOWN
                await self._handle_unknown_request(update)
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await update.message.reply_text(
                "😔 Извините, произошла ошибка при обработке вашего запроса. "
                "Пожалуйста, попробуйте позже."
            )
    
    async def _handle_profile_request(self, update: Update):
        """Handle profile information request"""
        await update.message.reply_text("🔍 Получаю информацию о вашем профиле...")
        
        try:
            profile_data = self.linkedin_service.get_my_profile()
            
            if profile_data.get("error"):
                await update.message.reply_text(
                    f"❌ Не удалось получить профиль: {profile_data['error']}\n\n"
                    "Убедитесь, что вы настроили LinkedIn URL через команду set_linkedin_url."
                )
                return
            
            response = self.openai_service.format_profile_response(profile_data)
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error fetching profile: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Не удалось получить профиль. Проверьте настройки подключения к LinkedIn."
            )
    
    async def _handle_jobs_request(self, update: Update, intent_result):
        """Handle job search request"""
        if not intent_result.job_params:
            await update.message.reply_text(
                "🤔 Не могу понять, какую вакансию вы ищете. "
                "Пожалуйста, укажите должность или роль.\n\n"
                "Например: 'Найди вакансии Python разработчика'"
            )
            return
        
        job_params = intent_result.job_params
        
        search_text = f"🔍 Ищу вакансии: {job_params.role}"
        if job_params.location:
            search_text += f" ({job_params.location})"
        
        await update.message.reply_text(search_text + "...")
        
        try:
            jobs = self.linkedin_service.search_jobs(
                query=job_params.role,
                location=job_params.location,
                keywords=job_params.keywords
            )
            
            response = self.openai_service.format_jobs_response(jobs)
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error searching jobs: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Не удалось выполнить поиск вакансий. Попробуйте позже."
            )
    
    async def _handle_unknown_request(self, update: Update):
        """Handle unknown intent"""
        response = """🤷‍♂️ Извините, я пока умею только:

📋 Показывать информацию о вашем профиле LinkedIn
💼 Искать вакансии на LinkedIn

Пожалуйста, переформулируйте ваш запрос.

Примеры:
• "Покажи мой профиль"
• "Найди вакансии Python разработчика"
• "Удалённая работа для дата сайентиста\""""
        
        await update.message.reply_text(response)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    
    def setup(self):
        """Setup bot handlers"""
        self.application = Application.builder().token(self.token).build()
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("seturl", self.seturl_command))
        self.application.add_handler(CommandHandler("refresh", self.refresh_command))
        
        # Message handler
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
        
        logger.info("Bot handlers setup complete")
    
    def run(self):
        """Run the bot"""
        if not self.application:
            self.setup()
        
        logger.info("Starting bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
