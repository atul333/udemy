import os
import sys
import logging
import asyncio
import aiohttp
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from scraper import get_courses
from datetime import datetime
import uuid
from telegram.constants import ParseMode

# Load environment variables from .env file
load_dotenv()

# Advertisement message
ADVERTISEMENT = """📢 Top Telegram Channels You Shouldn't Miss! 🔥
Join our most useful and trending Telegram channels for daily updates, learning, and growth 📚🚀

👇 Tap to join and never miss an update:

1️⃣ 🎯 UPSC & SSC CGL Quiz Preparation
🔍 Daily MCQs | PYQs | Exam Practice
👉 Join Now 👇
https://t.me/UPSC_SSC_Quiz_Preparation

2️⃣ 📈 Crypto News Daily
🪙 Latest Crypto Market Updates | Signals | News
👉 Join Now 👇
https://t.me/Crypto_News_Daily_2

3️⃣ 🇬🇧 English Grammar & GK Quiz
📝 Improve English & General Knowledge with fun quizzes
👉 Join Now 👇
https://t.me/English_Grammar_Quiz_GK

5️⃣ 📰 Current Affairs GK Free
📆 Daily Current Affairs | Important GK | Free PDFs
👉 Join Now 👇
https://t.me/current_affairs_gk_free

📌 Stay informed, stay ahead – All in one place! 🔔
💬 Share with friends & help them level up too!"""

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token and channel IDs — loaded from .env file
TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_IDS_RAW = os.getenv('CHANNEL_IDS', '')
CHANNEL_ID = tuple(c.strip() for c in CHANNEL_IDS_RAW.split(',') if c.strip())
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '300'))
AD_INTERVAL = int(os.getenv('AD_INTERVAL', '3600'))

# Validate required credentials at startup
if not TOKEN:
    sys.exit("❌ ERROR: BOT_TOKEN is not set. Please add it to your .env file.")
if not CHANNEL_ID:
    sys.exit("❌ ERROR: CHANNEL_IDS is not set. Please add it to your .env file.")

# Store last posted courses to avoid duplicates
last_posted_courses = set()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text('Hello! Welcome to Udemy Course Coupons Bot!\nUse /courses to see latest Udemy courses.')
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")

async def post_to_channel(context: ContextTypes.DEFAULT_TYPE, courses):
    try:
        if courses:
            for course in courses:
                if course.get('udemy_url'):
                    message = f'\n🔗 {course["udemy_url"]}'

                    
                    for channel in CHANNEL_ID:
                        try:
                            await context.bot.send_message(
                                chat_id=channel,
                                text=message,
                                disable_web_page_preview=False,
                                protect_content=True
                            )
                            # Add a small delay between messages to avoid rate limiting
                            await asyncio.sleep(1)
                        except Exception as channel_error:
                            logger.error(f"Error posting to channel {channel}: {str(channel_error)}")
                            continue  # Continue with next channel if one fails
    except Exception as e:
        logger.error(f"Error posting to channel: {str(e)}")
        logger.exception(e)  # Log full exception details

async def send_advertisement(context: ContextTypes.DEFAULT_TYPE):
    """Send advertisement message to all channels"""
    try:
        for channel in CHANNEL_ID:
            try:
                await context.bot.send_message(
                    chat_id=channel,
                    text=ADVERTISEMENT,
                    disable_web_page_preview=True,
                    parse_mode=ParseMode.HTML
                )
                logger.info(f"Advertisement sent to {channel}")
            except Exception as e:
                logger.error(f"Failed to send ad to {channel}: {str(e)}")
    except Exception as e:
        logger.error(f"Error in send_advertisement: {str(e)}")

async def check_new_courses(context: ContextTypes.DEFAULT_TYPE):
    global last_posted_courses
    try:
        logger.info("Checking for new courses...")
        courses = await get_courses()
        new_courses = [c for c in courses if c.get('udemy_url') and c['udemy_url'] not in last_posted_courses]
        
        if new_courses:
            await post_to_channel(context, new_courses)
            # Update last posted courses
            for course in new_courses:
                last_posted_courses.add(course['udemy_url'])
            logger.info(f"Posted {len(new_courses)} new courses to channel")
        else:
            logger.info("No new courses found")
            
    except Exception as e:
        logger.error(f"Error in check_new_courses: {str(e)}")

async def courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text('Fetching latest courses... Please wait.')
        courses_list = await get_courses(limit=5)
        if courses_list:
            message = 'Latest Udemy Courses:\n\n'
            for course in courses_list:
                if course.get('udemy_url'):
                    message += f"📚 {course['title']}\n🔗 {course['udemy_url']}\n\n"
            await update.message.reply_text(message, disable_web_page_preview=True)
        else:
            await update.message.reply_text('Sorry, unable to fetch courses at the moment.')
    except Exception as e:
        logger.error(f"Error in courses command: {str(e)}")
        await update.message.reply_text('An error occurred while fetching courses.')


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    import time
    while True:
        loop = None
        try:
            # Create a brand-new event loop each restart iteration.
            # This avoids "Event loop is closed" and
            # "Cannot close a running event loop" errors.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            application = Application.builder().token(TOKEN).build()

            # Add command handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("courses", courses))

            # Schedule jobs (intervals from .env)
            job_queue = application.job_queue
            job_queue.run_repeating(check_new_courses, interval=CHECK_INTERVAL, first=10)
            job_queue.run_repeating(send_advertisement, interval=AD_INTERVAL, first=AD_INTERVAL)

            application.add_error_handler(error_handler)

            logger.info('Bot is starting...')
            application.run_polling(allowed_updates=Update.ALL_TYPES)

        except Exception as e:
            logger.error(f"Critical error: {str(e)}")
            logger.info('Attempting to restart the bot in 5 seconds...')
            time.sleep(5)
        finally:
            # Cleanly close the loop before the next iteration
            try:
                if loop and not loop.is_closed():
                    loop.close()
            except Exception:
                pass


if __name__ == '__main__':
    main()