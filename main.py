import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger()

# Function to fetch live trading data with enhanced error handling
def fetch_live_trading_data(symbol):
    url = "https://www.sharesansar.com/live-trading"
    try:
        response = requests.get(url)
        response.raise_for_status()  # raises exception when not a 2xx response
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
        logger.error("No table found in live trading data.")
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
                logger.error(f"Error processing live trading data for symbol {symbol}: {e}")
                return None
    return None

# Use caching to store previously fetched data for a short time
stock_cache = {}

def fetch_stock_data(symbol):
    if symbol in stock_cache and time.time() - stock_cache[symbol]['timestamp'] < 60 * 5:
        # Cache is valid for 5 minutes
        logger.info(f"Fetching cached data for {symbol}")
        return stock_cache[symbol]['data']
    
    live_data = fetch_live_trading_data(symbol)
    if live_data:
        stock_cache[symbol] = {'data': live_data, 'timestamp': time.time()}
    return live_data

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# Main function
if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_API_KEY")

    # Set up Telegram bot application
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_symbol))

    # Start polling
    logger.info("Starting polling...")
    application.run_polling()
