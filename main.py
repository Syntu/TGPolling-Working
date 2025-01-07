import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Function to fetch NEPSE Alpha data
def fetch_nepse_alpha_data():
    url = "https://nepsealpha.com/live-market"
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    service = Service('path/to/chromedriver')  # Replace with your chromedriver path
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        time.sleep(5)  # Wait for the page to load

        # Extract required data
        data = {}
        data['Date'] = driver.find_element(By.XPATH, '//span[@id="marketDate"]').text
        data['Current'] = driver.find_element(By.XPATH, '//span[@id="marketCurrent"]').text
        data['Daily Gain'] = driver.find_element(By.XPATH, '//span[@id="dailyGain"]').text
        data['Turnover'] = driver.find_element(By.XPATH, '//span[@id="marketTurnover"]').text
        data['Previous Close'] = driver.find_element(By.XPATH, '//span[@id="previousClose"]').text
        data['Positive Stock'] = driver.find_element(By.XPATH, '//span[@id="positiveStock"]').text
        data['Neutral Stock'] = driver.find_element(By.XPATH, '//span[@id="neutralStock"]').text
        data['Negative Stock'] = driver.find_element(By.XPATH, '//span[@id="negativeStock"]').text

        response = (
            f"📊 **NEPSE Live Market Data**\n\n"
            f"🗓 Date: {data['Date']}\n"
            f"📈 Current: {data['Current']}\n"
            f"📉 Daily Gain: {data['Daily Gain']}\n"
            f"💰 Turnover: {data['Turnover']}\n"
            f"🔙 Previous Close: {data['Previous Close']}\n"
            f"✅ Positive Stocks: {data['Positive Stock']}\n"
            f"⚖ Neutral Stocks: {data['Neutral Stock']}\n"
            f"❌ Negative Stocks: {data['Negative Stock']}\n"
        )
        return response
    except Exception as e:
        return f"⚠️ Error fetching NEPSE Alpha data: {e}"
    finally:
        driver.quit()

# Function to fetch live trading data
def fetch_live_trading_data(symbol):
    url = "https://www.sharesansar.com/live-trading"
    response = requests.get(url)

    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
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
            except (ValueError, IndexError):
                return None
    return None

# Function to fetch 52-week data
def fetch_52_week_data(symbol):
    url = "https://www.sharesansar.com/today-share-price"
    response = requests.get(url)

    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
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
            except (ValueError, IndexError):
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
    welcome_message = (
        "Welcome 🙏 to NEPSE BOT\n"
        "के को डाटा चाहियो? Symbol दिनुस।\n"
        "NEPSE टाइप गरेमा बजारको डेटा आउँछ।\n"
        "अन्य Symbol टाइप गरेमा शेयर विवरण आउँछ।"
    )
    await update.message.reply_text(welcome_message)

# Default handler for stock symbol
async def handle_stock_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.strip().upper()

    if symbol == "NEPSE":
        response = fetch_nepse_alpha_data()
    else:
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
                "Thank you for using NEPSE BOT."
            )
        else:
            response = f"⚠️ Symbol '{symbol}' फेला परेन। कृपया सही Symbol टाइप गर्नुहोस्।"

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
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
