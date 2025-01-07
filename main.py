import os
import json
import smtplib
import schedule
import time
from threading import Thread
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Ensure users.json exists
DATA_FILE = "users.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as file:
        json.dump([], file)

# Environment variables
BOT_OWNER_CHAT_ID = os.getenv("BOT_OWNER_CHAT_ID")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")


# Function to log unique users
def log_user(chat_id, username):
    with open(DATA_FILE, "r") as file:
        users = json.load(file)

    if chat_id not in [user["chat_id"] for user in users]:
        users.append({"chat_id": chat_id, "username": username})
        with open(DATA_FILE, "w") as file:
            json.dump(users, file)
        # Notify bot owner about the new user
        asyncio.create_task(notify_owner(chat_id, username))


# Notify the bot owner about a new user
async def notify_owner(chat_id, username):
    await application.bot.send_message(
        chat_id=BOT_OWNER_CHAT_ID,
        text=f"New user detected:\nChat ID: {chat_id}\nUsername: {username}"
    )


# Send email with users.json
def send_email():
    if not os.path.exists(DATA_FILE):
        print("No users.json file found.")
        return

    with open(DATA_FILE, "r") as file:
        users = json.load(file)
    formatted_users = "\n".join([f"{user['chat_id']}: {user['username']}" for user in users])

    subject = "NEPSE Bot: Weekly Users Report"
    body = f"Attached is the weekly report of users who have used your bot.\n\nUser List:\n{formatted_users}"

    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    with open(DATA_FILE, "rb") as file:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file.read())
    encoders.encode_base64(part)
    part.add_header(
        'Content-Disposition',
        f'attachment; filename={DATA_FILE}'
    )
    msg.attach(part)

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


# Schedule email job
def schedule_email():
    schedule.every().thursday.at("16:00").do(send_email)

    while True:
        schedule.run_pending()
        time.sleep(1)


# Flask API endpoint to view users.json
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
    # Telegram bot application
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    # Add command handler
    application.add_handler(CommandHandler("start", start))

    # Start email scheduling in a separate thread
    email_thread = Thread(target=schedule_email)
    email_thread.daemon = True
    email_thread.start()

    # Start Telegram bot polling
    print("Starting polling...")
    application.run_polling()
