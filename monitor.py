import time
import os
import random
from dotenv import load_dotenv
from twilio.rest import Client
import requests

# Load Database
from database import Alert, User

# Load Config
load_dotenv(override=True)

# SETUP TWILIO
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone = os.getenv("TWILIO_PHONE")
client = Client(account_sid, auth_token)

def get_strategic_phrase(symbol, condition, price):
    """
    Returns a 'Bybit-Style' push notification phrase.
    """
    if condition == 'above':
        phrases = [
            f"🚀 *{symbol} is surging!* Price crossed above {price}",
            f"📈 *Bullish Alert:* {symbol} has broken resistance at {price}",
            f"🔥 *Market Move:* {symbol} is rallying past {price}",
            f"⚡ *Breakout:* {symbol} just spiked to {price}"
        ]
    else:
        phrases = [
            f"🔻 *{symbol} is dropping!* Price crossed below {price}",
            f"📉 *Bearish Alert:* {symbol} fell through support at {price}",
            f"🩸 *Market Dump:* {symbol} is sliding below {price}",
            f"⚠️ *Correction:* {symbol} dipped to {price}"
        ]
    return random.choice(phrases)

def get_batch_prices(symbols):
    """
    Fetch live prices for ALL symbols in one request.
    """
    if not symbols: return {}
    try:
        # Convert list to string: "BTCUSDT,ETHUSDT,MNTUSDT"
        sym_string = ",".join(symbols)
        url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={sym_string}"
        resp = requests.get(url).json()
        
        prices = {}
        if resp['retCode'] == 0:
            for item in resp['result']['list']:
                prices[item['symbol']] = float(item['lastPrice'])
        return prices
    except Exception as e:
        print(f"⚠️ Price Fetch Error: {e}")
        return {}

def check_markets():
    print("🛰️ Scanning Markets...")
    
    # 1. Find all active alerts
    alerts = Alert.select(Alert, User).join(User).where(Alert.is_active == True)
    if not alerts: return

    # 2. Get unique symbols to check (Optimization)
    unique_symbols = list(set([a.symbol for a in alerts]))
    
    # 3. Get Live Prices
    live_prices = get_batch_prices(unique_symbols)
    
    # 4. Check every alert against live prices
    for alert in alerts:
        symbol = alert.symbol
        if symbol not in live_prices: continue
            
        current_price = live_prices[symbol]
        target = alert.target_price
        triggered = False
        
        # LOGIC: Check if condition is met
        if alert.condition == 'above' and current_price >= target:
            triggered = True
        elif alert.condition == 'below' and current_price <= target:
            triggered = True
            
        if triggered:
            print(f"🚀 TRIGGERED: {symbol} @ {current_price}")
            
            # Send the Strategic Message
            phrase = get_strategic_phrase(symbol, alert.condition, target)
            send_whatsapp(alert.user.phone, phrase)
            
            # Deactivate alert
            alert.is_active = False
            alert.save()

def send_whatsapp(to_number, body_text):
    try:
        client.messages.create(
            from_=twilio_phone,
            body=body_text,
            to=f"whatsapp:{to_number}"
        )
    except Exception as e:
        print(f"❌ Twilio Error: {e}")

# --- MAIN LOOP ---
if __name__ == "__main__":
    print("✅ Strategic Monitor Active (Scanning every 10s)")
    while True:
        try:
            check_markets()
        except Exception as e:
            print(f"Critical Error: {e}")
        time.sleep(10)