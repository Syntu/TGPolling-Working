import os
import requests
from bs4 import BeautifulSoup
from flask import Flask
from telegram import Update, Bot, Chat
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Global variables to store user data
users = {}
active_users = set()

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

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    # Add new user to the database
    if chat_id not in users:
        users[chat_id] = {
            "full_name": user.full_name,
            "username": user.username,
            "user_id": user.id,
        }

        # Notify the bot owner about the new user
        owner_chat_id = os.getenv("BOT_OWNER_CHAT_ID")
        bot = context.bot
        message = (
            f"🎉 New User Alert!\n\n"
            f"Full Name: {user.full_name}\n"
            f"Username: @{user.username}\n"
            f"User ID: {user.id}"
        )
        await bot.send_message(chat_id=owner_chat_id, text=message)

    # Welcome message
    welcome_message = (
        "Welcome 🙏 to Syntoo's NEPSE BOT💗\n"
        "के को डाटा चाहियो? Symbol दिनुस।\n"
        "उदाहरण: SHINE, SCB, SWBBL, SHPC"
    )
    await update.message.reply_text(welcome_message)

# Command to get all users
async def get_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    owner_chat_id = int(os.getenv("BOT_OWNER_CHAT_ID"))

    if chat_id == owner_chat_id:
        message = f"Total Users: {len(users)}\n\n"
        for user_id, user_info in users.items():
            message += (
                f"Full Name: {user_info['full_name']}\n"
                f"Username: @{user_info['username']}\n"
                f"User ID: {user_info['user_id']}\n\n"
            )
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("⛔ यो आदेश तपाईँलाई उपलब्ध छैन।")

# Command to get active users
async def get_active_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    owner_chat_id = int(os.getenv("BOT_OWNER_CHAT_ID"))

    if chat_id == owner_chat_id:
        message = f"Active Users: {len(active_users)}\n\n"
        for active_user in active_users:
            user_info = users.get(active_user)
            if user_info:
                message += (
                    f"Full Name: {user_info['full_name']}\n"
                    f"Username: @{user_info['username']}\n"
                    f"User ID: {user_info['user_id']}\n\n"
                )
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("⛔ यो आदेश तपाईँलाई उपलब्ध छैन।")

# Handler for stock symbol
async def handle_stock_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    text = update.message.text.strip()

    # Handle group or private chat conditions
    if chat_type == Chat.PRIVATE:
        symbol = text.upper()
    elif chat_type in [Chat.GROUP, Chat.SUPERGROUP] and text.startswith("/"):
        symbol = text[1:].upper()
    else:
        return

    # Fetch stock data
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
            f"५२ हप्ताको धेरै मुल्यबाट घटेको: {data['Down From High']}%\n"
            f"५२ हप्ताको कम मुल्यबाट बढेको: {data['Up From Low']}%\n\n"
            "Thank you for using my bot. Please share it with your friends and groups."
        )
    else:
        response = f"""Symbol '{symbol}' 
        ल्या, फेला परेन त 🤗🤗।
        Symbol राम्रो सङ्ग फेरि हान्नुस है।
        कि कारोबार भएको छैन? 🤗। """
    await update.message.reply_text(response, parse_mode=ParseMode.HTML)

# Main function
if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_API_KEY")

    # Set up Telegram bot application
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", get_all_users))
    application.add_handler(CommandHandler("get_users", get_active_users))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_symbol))
    application.add_handler(MessageHandler(filters.COMMAND, handle_stock_symbol))

    # Start polling
    print("Starting polling...")
    application.run_polling()

    # Running Flask app to handle web traffic
    port = int(os.getenv("PORT", 8080))  # Render's default port
    app.run(host="0.0.0.0", port=port)
