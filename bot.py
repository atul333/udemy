import os
import logging
import asyncio
from telegram.ext import Application, CommandHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from scraper import get_courses
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token and channel ID
TOKEN = '7962778190:AAFC1pBpsVof7Gae73tKEflbF_EUCV6d6yc'
CHANNEL_ID = '@ENROLL_FREE_UDEMY_COURSES'

# Store last posted courses to avoid duplicates
last_posted_courses = set()

# Store course data with unique IDs
course_data = {}

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text('Hello! Welcome to Udemy Course Coupons Bot!\nUse /courses to see latest Udemy courses.')
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")

def format_course_message(courses):
    global course_data
    messages = []
    for course in courses:
        # Generate a unique ID for this course
        course_id = str(uuid.uuid4())
        # Store course URL with the unique ID
        course_data[course_id] = course["udemy_url"]
        
        message = (
            f'🎯 *{course["title"]}*\n\n'
            f'🌐 *Language: {course["language"]}*\n'
            f'⏰ *Added: {course["date"]}*\n'
            f'💎 *Status: AVAILABLE*\n'
            f'💰 *Price: FREE (Limited Time)* 🏷️\n\n'
            f'📢 *Share with your friends & colleagues!* 🤝\n'
            f'⭐️ *Learn, Grow & Succeed Together!* 🌟\n\n'
            f'═══════════════════════\n\n'
        )
        messages.append((message, course_id))
    return messages

async def post_to_channel(context: ContextTypes.DEFAULT_TYPE, courses):
    try:
        if courses:
            course_messages = format_course_message(courses)
            for message_text, course_id in course_messages:
                # Create inline keyboard with button
                keyboard = [
                    [InlineKeyboardButton("🔥 ENROLL NOW 🔥", url=course_data[course_id])]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=message_text,
                    parse_mode='Markdown',
                    disable_web_page_preview=True,
                    protect_content=True,
                    reply_markup=reply_markup
                )
    except Exception as e:
        logger.error(f"Error posting to channel: {str(e)}")
        logger.exception(e)  # Log full exception details

async def check_new_courses(context: ContextTypes.DEFAULT_TYPE):
    global last_posted_courses
    try:
        courses = get_courses()
        if courses:
            new_courses = []
            for course in courses:
                # Skip courses with no Udemy URL
                if not course['udemy_url']:
                    continue
                course_id = f"{course['title']}-{course['date']}"
                if course_id not in last_posted_courses:
                    new_courses.append(course)
                    last_posted_courses.add(course_id)
            
            if new_courses:
                await post_to_channel(context, new_courses)
                
            # Keep only recent courses in memory
            if len(last_posted_courses) > 100:
                last_posted_courses.clear()
                
    except Exception as e:
        logger.error(f"Error checking new courses: {str(e)}")

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
            
            # Add job for checking new courses every 5 seconds
            application.job_queue.run_repeating(check_new_courses, interval=5)

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