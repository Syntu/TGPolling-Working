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

# Track users
users = []

# Function to fetch live trading data
def fetch_live_trading_data(symbol):
    url = "https://www.sharesansar.com/live-trading"
    response = requests.get(url)

    if response.status_code != 200:
        print("Error: Unable to fetch live trading data. Status code:", response.status_code)
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
        print("Error: No table found in live trading data.")
        return None

    rows = table.find_all('tr')[1:]
    for row in rows:
        cols = row.find_all('td')
        row_symbol = cols[1].text.strip()

        if row_symbol.upper() == symbol.upper():
            try:
                ltp = float(cols[2].text.strip().replace(',', ''))
                change_percent = cols[4].text.strip()
                day_high = float(cols[6].text.strip().replace(',', ''))
                day_low = float(cols[7].text.strip().replace(',', ''))
                volume = cols[8].text.strip()
                previous_close = float(cols[9].text.strip().replace(',', ''))
                return {
                    'LTP': ltp,
                    'Change Percent': change_percent,
                    'Day High': day_high,
                    'Day Low': day_low,
                    'Volume': volume,
                    'Previous Close': previous_close
                }
            except (ValueError, IndexError) as e:
                print(f"Error processing live trading data for symbol {symbol}: {e}")
                return None
    return None

# Function to fetch 52-week data
def fetch_52_week_data(symbol):
    url = "https://www.sharesansar.com/today-share-price"
    response = requests.get(url)

    if response.status_code != 200:
        print("Error: Unable to fetch 52-week data. Status code:", response.status_code)
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
        print("Error: No table found in 52-week data.")
        return None

    rows = table.find_all('tr')[1:]
    for row in rows:
        cols = row.find_all('td')
        row_symbol = cols[1].text.strip()

        if row_symbol.upper() == symbol.upper():
            try:
                week_52_high = float(cols[19].text.strip().replace(',', ''))
                week_52_low = float(cols[20].text.strip().replace(',', ''))
                return {
                    '52 Week High': week_52_high,
                    '52 Week Low': week_52_low
                }
            except (ValueError, IndexError) as e:
                print(f"Error processing 52-week data for symbol {symbol}: {e}")
                return None
    return None

# Function to fetch complete stock data
def fetch_stock_data(symbol):
    live_data = fetch_live_trading_data(symbol)
    week_data = fetch_52_week_data(symbol)

    if live_data and week_data:
        ltp = live_data['LTP']
        week_52_high = week_data['52 Week High']
        week_52_low = week_data['52 Week Low']

        # Calculate down from high and up from low
        down_from_high = round(((week_52_high - ltp) / week_52_high) * 100, 2)
        up_from_low = round(((ltp - week_52_low) / week_52_low) * 100, 2)

        live_data.update(week_data)
        live_data.update({
            'Down From High': down_from_high,
            'Up From Low': up_from_low
        })
        return live_data
    return None

# Function to load users from a file
def load_users_from_file():
    if os.path.exists("users.txt"):
        with open("users.txt", "r") as file:
            for line in file:
                user_id, full_name = line.strip().split(",", 1)
                users.append({"id": int(user_id), "full_name": full_name})

# Function to save users to a file
def save_users_to_file():
    with open("users.txt", "w") as file:
        for user in users:
            file.write(f"{user['id']},{user['full_name']}\n")

# Add a new user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "Welcome 🙏 to Syntoo's NEPSE BOT💗\n"
        "के को डाटा चाहियो? Symbol दिनुस।\n"
        "उदाहरण: SHINE, SCB, SWBBL, SHPC"
    )
    await update.message.reply_text(welcome_message)

    user_id = update.message.chat.id
    full_name = update.message.chat.full_name

    # Check if the user is already added
    if user_id not in [user['id'] for user in users]:
        users.append({"id": user_id, "full_name": full_name})
        save_users_to_file()

        # Notify the owner about the new user
        owner_id = os.getenv("OWNER_ID")  # Add the owner's Telegram ID to .env
        message = f"New user joined!\nFull Name: {full_name}\nUser ID: {user_id}"
        await context.bot.send_message(chat_id=owner_id, text=message)

        print(f"New user added: {full_name} (ID: {user_id})")

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

# Command to view active users
async def get_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if users:
        user_list = "\n".join([f"Name: {user['full_name']} (ID: {user['id']})" for user in users])
        response = f"Active users:\n{user_list}"
    else:
        response = "No active users found."
    await update.message.reply_text(response)

# Send email with user details every Thursday at 1600
def send_email(user_details):
    sender_email = os.getenv("EMAIL_ADDRESS")
    receiver_email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "User Details Report"

    body = "Here are the user details:\n\n"
    for user in user_details:
        body += f"Name: {user['full_name']} (ID: {user['id']})\n"
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

# Scheduler to send email every Thursday at 1600
scheduler = BackgroundScheduler()

def schedule_email():
    scheduler.add_job(
        lambda: send_email(users), 'cron', day_of_week='thu', hour=16, minute=0
    )
    scheduler.start()

# Main function
if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_API_KEY")
    OWNER_ID = os.getenv("OWNER_ID")  # Ensure OWNER_ID is set in your .env file

    # Load existing users from file
    load_users_from_file()

    # Set up Telegram bot application
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_symbol))
    application.add_handler(CommandHandler("get_users", get_users))  # Command to view users

    # Start polling
    print("Starting polling...")
    application.run_polling()

    # Schedule weekly email
    schedule_email()

    # Running Flask app to handle web traffic
    port = int(os.getenv("PORT", 8080))  # Render's default port
