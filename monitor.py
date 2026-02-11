import time
import os
import random
import requests
from dotenv import load_dotenv
from twilio.rest import Client

# Load Database Models
from database import Alert, User, db

# Load Environment Config
load_dotenv(override=True)

# --- TWILIO SETUP ---
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone = os.getenv("TWILIO_PHONE")
client = Client(account_sid, auth_token)

# --- STRATEGIC NOTIFICATIONS ---

def get_strategic_phrase(symbol, condition, price):
    """
    Returns a high-impact notification phrase.
    """
    clean_sym = symbol.replace("USDT", "")
    if condition == 'above':
        phrases = [
            f"🚀 *{clean_sym} Surge Alert!* Price crossed above ${price:,.2f}",
            f"📈 *Bullish Momentum:* {clean_sym} broke resistance at ${price:,.2f}",
            f"🔥 *Breakout:* {clean_sym} is rallying past ${price:,.2f}",
            f"⚡ *Market Move:* {clean_sym} just spiked to ${price:,.2f}"
        ]
    else:
        phrases = [
            f"🔻 *{clean_sym} Drop Alert!* Price fell below ${price:,.2f}",
            f"📉 *Bearish Signal:* {clean_sym} slid through support at ${price:,.2f}",
            f"🩸 *Market Correction:* {clean_sym} is dipping below ${price:,.2f}",
            f"⚠️ *Price Alert:* {clean_sym} just hit ${price:,.2f}"
        ]
    return random.choice(phrases)

# --- PRICE DATA ENGINE ---

def get_batch_prices(symbols):
    """
    Fetch live prices for multiple symbols in a single high-speed Bybit V5 request.
    """
    if not symbols: return {}
    try:
        # Optimization: Fetch only the specific tickers needed
        sym_string = ",".join(symbols)
        url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={sym_string}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        prices = {}
        if data.get('retCode') == 0:
            for item in data['result']['list']:
                prices[item['symbol']] = float(item['lastPrice'])
        return prices
    except Exception as e:
        print(f"⚠️ Market Data Error: {e}")
        return {}

# --- MONITORING LOGIC ---

def check_markets():
    # Ensure database connection is fresh
    if db.is_closed():
        db.connect()

    # 1. Pull all active alerts with User info
    active_alerts = Alert.select(Alert, User).join(User).where(Alert.is_active == True)
    
    if not active_alerts:
        return

    # 2. Extract unique symbols for batch processing
    unique_symbols = list(set([a.symbol for a in active_alerts]))
    
    # 3. Get real-time prices
    live_prices = get_batch_prices(unique_symbols)
    
    # 4. Process each alert
    for alert in active_alerts:
        symbol = alert.symbol
        if symbol not in live_prices:
            continue
            
        current_price = live_prices[symbol]
        target = alert.target_price
        triggered = False
        
        # Check condition
        if alert.condition == 'above' and current_price >= target:
            triggered = True
        elif alert.condition == 'below' and current_price <= target:
            triggered = True
            
        if triggered:
            print(f"✅ ALERT TRIGGERED: {symbol} at {current_price}")
            
            # Formulate and Send Notification
            phrase = get_strategic_phrase(symbol, alert.condition, target)
            phrase += f"\n\n💰 Current Rate: `${current_price:,.2f}`\n🔗 Trade on *PPAY*"
            
            send_whatsapp(alert.user.phone, phrase)
            
            # Deactivate to prevent spamming
            alert.is_active = False
            alert.save()

def send_whatsapp(to_number, body_text):
    """
    Sends the WhatsApp message via Twilio.
    """
    try:
        client.messages.create(
            from_=f"whatsapp:{twilio_phone}",
            body=body_text,
            to=f"whatsapp:{to_number}"
        )
    except Exception as e:
        print(f"❌ WhatsApp Delivery Failed for {to_number}: {e}")

# --- EXECUTION LOOP ---

if __name__ == "__main__":
    print(f"🚀 PPAY Market Monitor Online")
    print(f"📡 Scanning {os.getenv('ENV', 'Production')} Environment...")
    
    heartbeat_counter = 0
    
    while True:
        try:
            check_markets()
            
            # Log a heartbeat every 10 iterations (approx 1.5 mins)
            heartbeat_counter += 1
            if heartbeat_counter >= 10:
                print("💓 Monitor Heartbeat: OK")
                heartbeat_counter = 0
                
        except Exception as e:
            print(f"🛑 CRITICAL MONITOR ERROR: {e}")
            time.sleep(5) # Cooldown before retry
            
        time.sleep(10) # 10-second scan interval (optimized for rate limits)