import os
import logging
from telegram.ext import Application, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes
from scraper import get_courses

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
TOKEN = '7962778190:AAFC1pBpsVof7Gae73tKEflbF_EUCV6d6yc'

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text('Hello! Welcome to Udemy Course Coupons Bot!\nUse /courses to see latest Udemy courses.')
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")

async def courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text('Fetching latest courses... Please wait.')
        courses = get_courses()
        if courses:
            message = 'Latest Udemy Courses:\n\n'
            for course in courses:
                message += (
                    f'📚 {course["title"]}\n'
                    f'📅 {course["date"]}\n'
                    f'🏷️ Category: {course["category"].title()}\n'
                    f'🔗 {course["udemy_url"]}\n\n'
                )
            await update.message.reply_text(message, disable_web_page_preview=True)
        else:
            await update.message.reply_text('Sorry, unable to fetch courses at the moment.')
    except Exception as e:
        logger.error(f"Error in courses command: {str(e)}")
        await update.message.reply_text('An error occurred while fetching courses.')

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    while True:
        try:
            # Create application
            application = Application.builder().token(TOKEN).build()

            # Add command handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("courses", courses))

            # Add error handler
            application.add_error_handler(error_handler)

            # Start the bot
            logger.info('Bot is starting...')
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"Critical error: {str(e)}")
            # Wait for a moment before restarting
            import time
            time.sleep(5)
            logger.info('Attempting to restart the bot...')
            continue

if __name__ == '__main__':
    main()