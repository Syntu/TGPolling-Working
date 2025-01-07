import os
import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import schedule
import time
from threading import Thread

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Ensure users.json exists
DATA_FILE = "users.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as file:
        json.dump([], file)

# Bot owner chat ID (set in .env file)
BOT_OWNER_CHAT_ID = os.getenv("BOT_OWNER_CHAT_ID")

# Email configuration
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")  # Your email address
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Your email password (or app-specific password)

# Function to log unique users
def log_user(chat_id, username):
    with open(DATA_FILE, "r") as file:
        users = json.load(file)

    # Notify owner for new user
    if chat_id not in [user["chat_id"] for user in users]:
        users.append({"chat_id": chat_id, "username": username})
        with open(DATA_FILE, "w") as file:
            json.dump(users, file)
        # Notify bot owner about new user
        asyncio.run(notify_owner(chat_id, username))

# Async function to notify bot owner of new user
async def notify_owner(chat_id, username):
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_API_KEY")).build()
    await application.bot.send_message(
        chat_id=BOT_OWNER_CHAT_ID,
        text=f"New user detected:\nChat ID: {chat_id}\nUsername: {username}"
    )

# Send users.json via email
def send_email():
    if not os.path.exists(DATA_FILE):
        print("No users.json file found.")
        return

    # Read users and format in tabular form
    with open(DATA_FILE, "r") as file:
        users = json.load(file)
    formatted_users = "\n".join([f"{user['chat_id']}: {user['username']}" for user in users])

    # Create email message
    subject = "NEPSE Bot: Weekly Users Report"
    body = f"Attached is the weekly report of users who have used your bot.\n\nUser List:\n{formatted_users}"

    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # Attach users.json file
    with open(DATA_FILE, "rb") as file:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file.read())
    encoders.encode_base64(part)
    part.add_header(
        'Content-Disposition',
        f'attachment; filename={DATA_FILE}'
    )
    msg.attach(part)

    # Send email
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Schedule the email job
def schedule_email():
    schedule.every().thursday.at("16:00").do(send_email)

    while True:
        schedule.run_pending()
        time.sleep(1)

# API Endpoint to view users.json
@app.route("/users", methods=["GET"])
def get_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            users = json.load(file)
        return jsonify({"users": users, "total_users": len(users)}), 200
    return jsonify({"error": "users.json not found!"}), 404

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"
    log_user(chat_id, username)

    welcome_message = (
        "Welcome 🙏 to Syntoo's NEPSE BOT💗\n"
        "के को डाटा चाहियो? Symbol दिनुस।\n"
        "उदाहरण: SHINE, SCB, SWBBL, SHPC"
    )
    await update.message.reply_text(welcome_message)

# Main function
if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_API_KEY")

    # Set up Telegram bot application
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start))

    # Start email scheduling in a separate thread
    email_thread = Thread(target=schedule_email)
    email_thread.daemon = True
    email_thread.start()

    # Start polling
    print("Starting polling...")
    application.run_polling()

    # Running Flask app to handle web traffic
    port = int(os.getenv("PORT", 8080))  # Render's default port
    app.run(host="0.0.0.0", port=port)
