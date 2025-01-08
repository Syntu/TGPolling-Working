import os
import json
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio

# Load environment variables
load_dotenv()

# Environment Variables
TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")
BOT_OWNER_CHAT_ID = os.getenv("BOT_OWNER_CHAT_ID")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
PORT = os.getenv("PORT", 8080)

# Initialize Flask application
app = Flask(__name__)

# Load user details from file
def load_user_details():
    try:
        with open("user_details.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Save user details to file
def save_user_details():
    with open("user_details.json", "w") as file:
        json.dump(user_details, file, indent=4)

# Send user details via email
def send_user_details_email():
    try:
        if not user_details:
            print("No user details to send via email.")
            return
        
        # Prepare user details for email
        user_list = "\n".join([f"{i+1}. {user['name']} (ID: {user['id']})" for i, user in enumerate(user_details)])
        email_body = f"Total Users: {len(user_details)}\n\nUser Details:\n{user_list}"

        # Create email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_ADDRESS
        msg['Subject'] = "Weekly User Details"

        msg.attach(MIMEText(email_body, 'plain'))

        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("User details email sent successfully.")
    except Exception as e:
        print(f"Error sending user details email: {e}")

# Initialize user details
user_details = load_user_details()

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = {"name": user.full_name, "id": user.id}
    
    # Check if user is already in the list
    if user_info not in user_details:
        user_details.append(user_info)
        save_user_details()  # Save the updated list to file

        # Notify bot owner about new user
        owner_message = f"New User:\nName: {user.full_name}\nUser ID: {user.id}"
        await context.bot.send_message(chat_id=BOT_OWNER_CHAT_ID, text=owner_message)

    welcome_message = (
        "Welcome 🙏 to Syntoo's NEPSE BOT💗\n"
        "के को डाटा चाहियो? Symbol दिनुस।\n"
        "उदाहरण: SHINE, SCB, SWBBL, SHPC"
    )
    await update.message.reply_text(welcome_message)

# Default handler for stock symbol
async def handle_stock_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.strip().upper()
    data = fetch_stock_data(symbol)

    if data:
        response = (
            f"Stock Data for <b>{symbol}</b>:\n\n"
            f"LTP: {data['LTP']}\n"
            f"Change Percent: {data['Change Percent']}\n"
            f"Previous Close: {data['Previous Close']}\n"
            f"Day High: {data['Day High']}\n"
            f"Day Low: {data['Day Low']}\n"
            f"52 Week High: {data['52 Week High']}\n"
            f"52 Week Low: {data['52 Week Low']}\n"
            f"Volume: {data['Volume']}\n"
            f"५२ हप्ताको उच्च मुल्यबाट घटेको: {data['Down From High']}%\n"
            f"५२ हप्ताको न्युन मुल्यबाट बढेको: {data['Up From Low']}%\n\n"
            "Thank you for using my bot. Please share it with your friends and groups."
        )
    else:
        response = f"""Symbol '{symbol}' 
        ल्या, फेला परेन त 🤗🤗।
        Symbol राम्रो सङ्ग फेरि हान्नुस है।
        कि कारोबार भएको छैन? 🤗। """

    await update.message.reply_text(response, parse_mode=ParseMode.HTML)

# Handler to check total users
async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) == BOT_OWNER_CHAT_ID:  # Check if the user is the bot owner
        if user_details:
            total = len(user_details)
            user_list = "\n".join([f"{i+1}. {user['name']} (ID: {user['id']})" for i, user in enumerate(user_details)])
            response = f"Total Users: {total}\n\nUser Details:\n{user_list}"
        else:
            response = "No users have used the bot yet."
    else:
        response = "You are not authorized to view this information."
    await update.message.reply_text(response)

# Function to fetch stock data (dummy implementation for now)
def fetch_stock_data(symbol):
    return {
        'LTP': 1000,
        'Change Percent': '+2%',
        'Previous Close': 980,
        'Day High': 1020,
        'Day Low': 990,
        '52 Week High': 1200,
        '52 Week Low': 800,
        'Volume': '50,000',
        'Down From High': 16.67,
        'Up From Low': 25.0
    }

# Main function
if __name__ == "__main__":
    # Set up Telegram bot application
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_symbol))
    application.add_handler(CommandHandler("users", total_users))

    # Scheduler for weekly email
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_user_details_email, 'cron', day_of_week='thu', hour=16, minute=0)
    scheduler.start()

    # Start polling
    print("Starting polling...")
    asyncio.run(application.run_polling())

    # Running Flask app to handle web traffic
    app.run(host="0.0.0.0", port=PORT)
