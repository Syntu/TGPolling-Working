import os
import requests
from bs4 import BeautifulSoup
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Bot owner chat ID
BOT_OWNER_CHAT_ID = int(os.getenv("OWNER_ID"))

# User tracking
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

# Notify bot owner about a new user
async def notify_owner(user_id, full_name, username):
    message = (
        f"New User:\n"
        f"Full Name: {full_name}\n"
        f"Username: @{username or 'Not set'}\n"
        f"User ID: {user_id}"
    )
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_API_KEY")).build()
    await application.bot.send_message(chat_id=BOT_OWNER_CHAT_ID, text=message)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    full_name = update.message.chat.full_name
    username = update.message.chat.username

    # Add user to the list
    if user_id not in [user['id'] for user in users]:
        users.append({'id': user_id, 'name': full_name, 'username': username})
        await notify_owner(user_id, full_name, username)

    welcome_message = (
        "Welcome 🙏 to Syntoo's NEPSE BOT💗\n"
        "के को डाटा चाहियो? Symbol दिनुस।\n"
        "उदाहरण: SHINE, SCB, SWBBL, SHPC"
    )
    await update.message.reply_text(welcome_message)

# Handle stock symbol requests
async def handle_stock_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_group = update.message.chat.type in ["group", "supergroup"]

    if is_group and not update.message.text.startswith('/'):
        return

    symbol = update.message.text.strip().lstrip('/').upper()

    if not symbol:
        await update.message.reply_text("Please provide a valid stock symbol.")
        return

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
            f"५२ हप्ताको उच्च मुल्यबाट घटेको: {data['Down From High']}%\n"
            f"५२ हप्ताको न्युन मुल्यबाट बढेको: {data['Up From Low']}%\n\n"
            "Thank you for using my bot."
        )
    else:
        response = f"Symbol '{symbol}' फेला परेन। कृपया सही Symbol दिनुहोस्।"

    await update.message.reply_text(response, parse_mode=ParseMode.HTML)

# Send users' details
async def send_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != BOT_OWNER_CHAT_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    user_details = "\n".join(
        [f"👤 {user['name']} | @{user['username'] or 'Not set'} | 🆔 {user['id']}" for user in users]
    )
    response = f"👥 Total Users: {len(users)}\n\n{user_details}"
    await update.message.reply_text(response)

# Main function
if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_API_KEY")

    # Set up Telegram bot application
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_symbol))
    application.add_handler(CommandHandler("users", send_users))

    # Start polling
    application.run_polling()
