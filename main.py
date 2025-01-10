import os
import requests
from bs4 import BeautifulSoup
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Track new users
users = {}

# Load users from a file
def load_users_from_file():
    if os.path.exists("users.txt"):
        with open("users.txt", "r") as file:
            for line in file:
                user_id, username = line.strip().split(",")
                users[int(user_id)] = username

# Save users to a file
def save_users_to_file():
    with open("users.txt", "w") as file:
        for user_id, username in users.items():
            file.write(f"{user_id},{username}\n")

# Load users at startup
load_users_from_file()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "Welcome 🙏 to Syntoo's NEPSE BOT💗\n"
        "के को डाटा चाहियो? Symbol दिनुस।\n"
        "उदाहरण: SHINE, SCB, SWBBL, SHPC"
    )
    await update.message.reply_text(welcome_message)

    # Add new user to the list
    user_id = update.message.chat.id
    username = update.message.chat.username or "No Username"
    
    if user_id not in users:
        users[user_id] = username
        save_users_to_file()  # Save the updated user list to file
        print(f"New user added: {user_id} - {username}")
        
        # Send a message to the owner when a new user joins
        owner_id = os.getenv("OWNER_TELEGRAM_ID")
        owner_message = f"New user joined: \nUser ID: {user_id}\nUsername: {username}"
        await context.bot.send_message(chat_id=owner_id, text=owner_message)

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

async def send_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_id = os.getenv("OWNER_TELEGRAM_ID")
    if str(update.message.chat.id) != owner_id:
        await update.message.reply_text("Sorry, you are not authorized to use this command.")
        return

    if users:
        user_details = "\n".join([f"ID: {user_id}, Username: {username}" for user_id, username in users.items()])
        total_users = len(users)

        response = f"Total Users: {total_users}\n\nUser Details:\n{user_details}"
        await context.bot.send_message(chat_id=owner_id, text=response)
    else:
        await update.message.reply_text("No users found.")

# Send email with user details
def send_email_with_users():
    sender_email = os.getenv("EMAIL_ADDRESS")
    receiver_email = os.getenv("OWNER_EMAIL")  # Owner's email
    password = os.getenv("EMAIL_PASSWORD")

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "Telegram Bot User Details"

    body = f"Total Users: {len(users)}\n\n"
    for user_id, username in users.items():
        body += f"ID: {user_id}, Username: {username}\n"
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

# Scheduler to send email every Thursday
scheduler = BackgroundScheduler()

def schedule_user_email():
    scheduler.add_job(
        send_email_with_users, 'cron', day_of_week='thu', hour=16, minute=0
    )
    scheduler.start()

# Main function
if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_API_KEY")

    # Set up Telegram bot application
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_symbol))
    application.add_handler(CommandHandler("user", send_user_details))

    # Start polling
    print("Starting polling...")
    application.run_polling()

    # Schedule email
    schedule_user_email()

    # Running Flask app to handle web traffic
    port = int(os.getenv("PORT", 8080))  # Render's default port
    app.run(host="0.0.0.0", port=port)
