import os
import sqlite3
import requests
from bs4 import BeautifulSoup
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Create or connect to the database
def create_db():
    conn = sqlite3.connect('users.db')  # Database file
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY, 
                        username TEXT)''')
    conn.commit()
    conn.close()

# Add user to database
def add_user(user_id, username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

# Get total users
def get_total_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    conn.close()
    return total_users

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
    # Add user to database
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    add_user(user_id, username)

    welcome_message = (
        "Welcome ðŸ™ to Syntoo's NEPSE BOTðŸ’—\n"
        "à¤•à¥‡ à¤•à¥‹ à¤¡à¤¾à¤Ÿà¤¾ à¤šà¤¾à¤¹à¤¿à¤¯à¥‹? Symbol à¤¦à¤¿à¤¨à¥à¤¸à¥¤\n"
        "à¤‰à¤¦à¤¾à¤¹à¤°à¤£: SHINE, SCB, SWBBL, SHPC"
    )
    await update.message.reply_text(welcome_message)

    # Send message about total users to you
    total_users = get_total_users()
    chat_id = os.getenv("CHAT_ID")
    await context.bot.send_message(chat_id=chat_id, text=f"Total users using the bot: {total_users}")

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
            f"à¥«à¥¨ à¤¹à¤ªà¥à¤¤à¤¾à¤•à¥‹ à¤‰à¤šà¥à¤š à¤®à¥à¤²à¥à¤¯à¤¬à¤¾à¤Ÿ à¤˜à¤Ÿà¥‡à¤•à¥‹: {data['Down From High']}%\n"
            f"à¥«à¥¨ à¤¹à¤ªà¥à¤¤à¤¾à¤•à¥‹ à¤¨à¥à¤¯à¥à¤¨ à¤®à¥à¤²à¥à¤¯à¤¬à¤¾à¤Ÿ à¤¬à¤¢à¥‡à¤•à¥‹: {data['Up From Low']}%\n\n"
            "Thank you for using my bot. Please share it with your friends and groups."
        )
    else:
        response = f"""Symbol '{symbol}' 
        à¤²à¥à¤¯à¤¾, à¤«à¥‡à¤²à¤¾ à¤ªà¤°à¥‡à¤¨ à¤¤ ðŸ¤—ðŸ¤—à¥¤
        Symbol à¤°à¤¾à¤®à¥à¤°à¥‹ à¤¸à¤™à¥à¤— à¤«à¥‡à¤°à¤¿ à¤¹à¤¾à¤¨à¥à¤¨à¥à¤¸ à¤¹à¥ˆà¥¤
        à¤•à¤¿ à¤•à¤¾à¤°à¥‹à¤¬à¤¾à¤° à¤­à¤à¤•à¥‹ à¤›à¥ˆà¤¨? ðŸ¤—à¥¤ """

    await update.message.reply_text(response, parse_mode=ParseMode.HTML)

# Main function
if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_API_KEY")

    # Set up Telegram bot application
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_symbol))

    # Start polling
    print("Starting polling...")
    application.run_polling()

    # Running Flask app to handle web traffic
    port = int(os.getenv("PORT", 8080))  # Render's default port
    app.run(host="0.0.0.0", port=port)
