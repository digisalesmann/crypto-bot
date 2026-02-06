import os
import sys

# --- CONTENT DEFINITIONS ---

requirements_txt = """flask
twilio
ccxt
python-dotenv
peewee
schedule
"""

env_template = """# SECURITY WARNING: Keep this file private. Do not commit to git.
# Exchange Configuration (Binance, Kraken, Coinbase, etc.)
EXCHANGE_ID=binance
API_KEY=your_actual_api_key_here
API_SECRET=your_actual_api_secret_here

# Twilio Configuration (From Twilio Console)
TWILIO_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_FROM=whatsapp:+14155238886

# Bot Security
# Your personal WhatsApp number (e.g., +15551234567)
OWNER_PHONE=+15551234567
"""

gitignore_content = """__pycache__/
*.pyc
.env
bot.db
"""

config_py = """import os
from dotenv import load_dotenv

load_dotenv()

# Load Config
EXCHANGE_ID = os.getenv('EXCHANGE_ID', 'binance')
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
OWNER_PHONE = os.getenv('OWNER_PHONE')

# Twilio
TWILIO_SID = os.getenv('TWILIO_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM = os.getenv('TWILIO_FROM')
"""

database_py = """from peewee import *
import datetime

db = SqliteDatabase('bot.db')

class Alert(Model):
    symbol = CharField()
    target_price = FloatField()
    condition = CharField()  # 'above' or 'below'
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db

def initialize_db():
    db.connect()
    db.create_tables([Alert], safe=True)
    db.close()
"""

exchange_py = """import ccxt
import config

def get_exchange():
    try:
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
        exchange = exchange_class({
            'apiKey': config.API_KEY,
            'secret': config.API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'} 
        })
        return exchange
    except Exception as e:
        print(f"Error initializing exchange: {e}")
        return None

def get_price(symbol):
    exchange = get_exchange()
    ticker = exchange.fetch_ticker(symbol)
    return ticker['last']

def get_balance():
    exchange = get_exchange()
    balance = exchange.fetch_balance()
    total = balance['total']
    # Return only coins with balance > 0
    return {k: v for k, v in total.items() if v > 0}

def execute_trade(symbol, side, amount):
    exchange = get_exchange()
    # Market order
    order = exchange.create_order(symbol, 'market', side, amount)
    return order
"""

app_py = """from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import config
import exchange
import database
from database import Alert

app = Flask(__name__)
database.initialize_db()

@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').lower().strip()
    sender = request.values.get('From', '')

    resp = MessagingResponse()
    msg = resp.message()

    # SECURITY: Whitelist check
    if config.OWNER_PHONE not in sender:
        msg.body("⛔ Unauthorized access.")
        return str(resp)

    try:
        # 1. PRICE CHECK
        if incoming_msg.startswith('price'):
            # usage: price btc/usdt
            parts = incoming_msg.split()
            if len(parts) < 2:
                msg.body("⚠️ Usage: price BTC/USDT")
            else:
                symbol = parts[1].upper()
                price = exchange.get_price(symbol)
                msg.body(f"💎 {symbol}: ${price}")

        # 2. BALANCE CHECK
        elif incoming_msg == 'balance':
            bal = exchange.get_balance()
            if not bal:
                msg.body("💰 Wallet is empty.")
            else:
                txt = "💰 Your Wallet:\\n"
                for coin, amount in bal.items():
                    txt += f"- {coin}: {amount}\\n"
                msg.body(txt)

        # 3. TRADING (Buy/Sell)
        elif incoming_msg.startswith('buy') or incoming_msg.startswith('sell'):
            # usage: buy btc/usdt 0.001
            parts = incoming_msg.split()
            if len(parts) < 3:
                msg.body("⚠️ Usage: buy SYMBOL AMOUNT")
            else:
                side = parts[0]
                symbol = parts[1].upper()
                amount = float(parts[2])
                order = exchange.execute_trade(symbol, side, amount)
                msg.body(f"✅ {side.upper()} Executed!\\nID: {order['id']}\\nPrice: {order['average']}")

        # 4. SET ALERT
        elif incoming_msg.startswith('alert'):
            # usage: alert btc/usdt > 50000
            parts = incoming_msg.split()
            if len(parts) < 4:
                msg.body("⚠️ Usage: alert SYMBOL > PRICE")
            else:
                symbol = parts[1].upper()
                operator = parts[2]
                target = float(parts[3])
                condition = 'above' if '>' in operator else 'below'
                
                Alert.create(symbol=symbol, target_price=target, condition=condition)
                msg.body(f"🔔 Alert Set: Notify when {symbol} is {condition} ${target}")

        elif 'help' in incoming_msg:
            msg.body("🤖 Commands:\\n1. price BTC/USDT\\n2. balance\\n3. buy BTC/USDT 0.001\\n4. alert BTC/USDT > 90000")
            
        else:
            msg.body("❓ Unknown command. Type 'help'.")

    except Exception as e:
        msg.body(f"⚠️ Error: {str(e)}")

    return str(resp)

if __name__ == '__main__':
    print("🚀 Bot Server Running on Port 5000")
    app.run(port=5000, debug=True)
"""

monitor_py = """import time
import schedule
from twilio.rest import Client
import config
import exchange
from database import Alert

print("👀 Monitor Service Started...")

def check_alerts():
    try:
        active_alerts = Alert.select().where(Alert.is_active == True)
        count = active_alerts.count()
        if count == 0:
            return 

        print(f"Checking {count} active alerts...")

        # Initialize Twilio Client
        if not config.TWILIO_SID or not config.TWILIO_AUTH_TOKEN:
            print("⚠️ Twilio credentials missing in .env")
            return

        client = Client(config.TWILIO_SID, config.TWILIO_AUTH_TOKEN)

        for alert in active_alerts:
            current_price = exchange.get_price(alert.symbol)
            triggered = False
            
            if alert.condition == 'above' and current_price > alert.target_price:
                triggered = True
            elif alert.condition == 'below' and current_price < alert.target_price:
                triggered = True
                
            if triggered:
                msg_body = f"🚨 ALERT: {alert.symbol} hit ${current_price} (Target: ${alert.target_price})"
                print(msg_body)
                
                # Send WhatsApp
                client.messages.create(
                    from_=config.TWILIO_FROM,
                    to=f"whatsapp:{config.OWNER_PHONE}",
                    body=msg_body
                )
                
                # Deactivate
                alert.is_active = False
                alert.save()

    except Exception as e:
        print(f"Monitor Loop Error: {e}")

# Run check every 30 seconds
schedule.every(30).seconds.do(check_alerts)

while True:
    schedule.run_pending()
    time.sleep(1)
"""

# --- FILE CREATION LOGIC ---

def create_file(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Created: {filename}")

def main():
    print("🤖 Initializing WhatsApp Crypto Bot Project...")
    
    # Create Files
    create_file('requirements.txt', requirements_txt)
    create_file('.env', env_template)
    create_file('.gitignore', gitignore_content)
    create_file('config.py', config_py)
    create_file('database.py', database_py)
    create_file('exchange.py', exchange_py)
    create_file('app.py', app_py)
    create_file('monitor.py', monitor_py)

    print("\n" + "="*40)
    print("🎉 Project Setup Complete!")
    print("="*40)
    print("\nNext Steps:")
    print("1. Open the file '.env' and add your API Keys.")
    print("2. Install dependencies:")
    print("   pip install -r requirements.txt")
    print("3. Run the Web Server (Terminal 1):")
    print("   python app.py")
    print("4. Run the Monitor (Terminal 2):")
    print("   python monitor.py")

if __name__ == "__main__":
    main()