
# --- Provider Switch: 'bybit' or 'coingecko' ---
PROVIDER = 'coingecko'  # Change to 'bybit' to revert

import requests
from services.coingecko_price import CoinGeckoPriceService

# Base URL for Bybit V5 API
BASE_URL = "https://api.bybit.com/v5/market"

# Initialize CoinGecko service
cg_service = CoinGeckoPriceService()

def get_price(symbol):
    """Fetches live price using selected provider."""
    print(f"[DEBUG] get_price called with symbol='{symbol}', PROVIDER='coingecko' (forced)")
    # Always use CoinGecko for price
    clean = symbol.strip().lower().replace('/', '')
    price = cg_service.get_price(clean)
    if price is not None:
        return f"💎 *{clean.upper()} Live*\n💰 Price: *${float(price):,.4f}*\n(Source: CoinGecko)"
    else:
        return f"⚠️ Symbol *{clean.upper()}* not found on CoinGecko."

def fetch_raw_price(symbol):
    """Helper for Alerts/Swaps: Returns just the float number"""
    try:
        clean = symbol.upper().replace("/", "")
        if not clean.endswith("USDT"):
            clean += "USDT"
            
        url = f"{BASE_URL}/tickers?category=spot&symbol={clean}"
        response = requests.get(url, timeout=5).json()
        
        if response['retCode'] == 0:
            return float(response['result']['list'][0]['lastPrice'])
        return None
    except Exception as e:
        print(f"❌ Raw Price Error: {e}")
        return None

def get_top_gainers():
    """Returns top 5 gainers"""
    try:
        url = f"{BASE_URL}/tickers?category=spot"
        response = requests.get(url, timeout=5).json()
        
        tickers = response['result']['list']
        # Filter for USDT pairs only to keep list clean
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
        
        # Sort by change %
        usdt_pairs.sort(key=lambda x: float(x['price24hPcnt']), reverse=True)
        
        msg = "🚀 *Top Market Movers*\n━━━━━━━━━━━━━━━━\n"
        for i in range(5):
            t = usdt_pairs[i]
            change = float(t['price24hPcnt']) * 100
            price = float(t['lastPrice'])
            msg += f"{i+1}. *{t['symbol']}*: +{change:.1f}% (${price})\n"
            
        return msg
    except Exception as e:
        print(f"❌ Top Gainers Error: {e}")
        return "⚠️ Could not fetch market data."