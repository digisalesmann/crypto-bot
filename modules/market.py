import requests
import os
from services.coingecko_price import CoinGeckoPriceService

# 1. Config & Initialization
BASE_URL = "https://api.bybit.com/v5/market"
cg_service = CoinGeckoPriceService()

# Toggle this for high-level price lookups
# Bybit is better for trading pairs; CoinGecko is better for global averages.
PROVIDER = 'coingecko' 

def get_price(symbol):
    """
    User Command: price [COIN]
    Formatted for readability and branded for PPAY.
    """
    clean = symbol.strip().lower().replace('/', '').replace('usdt', '')
    print(f"[DEBUG] Fetching public price for: {clean}")

    # Use CoinGecko for broad market reach
    price = cg_service.get_price(clean)
    
    if price is not None:
        return (
            f"💎 *{clean.upper()} Market Rate*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💰 Price: *${float(price):,.4f}*\n"
            f"📈 Source: *CoinGecko Global*"
        )
    else:
        # Fallback to Bybit if CoinGecko fails to find the specific ticker
        raw = fetch_raw_price(clean)
        if raw:
            return (
                f"💎 *{clean.upper()} Market Rate*\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"💰 Price: *${float(raw):,.4f}*\n"
                f"📈 Source: *Bybit Spot*"
            )
        return f"⚠️ Symbol *{clean.upper()}* could not be located on our price feeds."

def fetch_raw_price(symbol):
    """
    Internal Helper: Used for Swaps, Alerts, and Math.
    Returns a clean float or None.
    """
    try:
        # Normalize for Bybit (e.g., BTC -> BTCUSDT)
        clean = symbol.upper().replace("/", "")
        if not clean.endswith("USDT") and clean not in ['USDT', 'USDC']:
            clean += "USDT"
            
        url = f"{BASE_URL}/tickers?category=spot&symbol={clean}"
        response = requests.get(url, timeout=5).json()
        
        if response.get('retCode') == 0 and response['result']['list']:
            return float(response['result']['list'][0]['lastPrice'])
        return None
    except Exception as e:
        print(f"❌ Bybit Fetch Error: {e}")
        return None

def get_top_gainers():
    """
    Market Insight: Returns top 5 movers in the last 24h.
    """
    try:
        url = f"{BASE_URL}/tickers?category=spot"
        response = requests.get(url, timeout=5).json()
        
        if response.get('retCode') != 0:
            return "⚠️ Market data temporarily unavailable."

        tickers = response['result']['list']
        # Filter for USDT pairs to avoid confusing users with BTC/ETH pairs
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
        
        # Sort by 24h Percentage Change
        usdt_pairs.sort(key=lambda x: float(x['price24hPcnt']), reverse=True)
        
        msg = "🚀 *PPAY Top Gainers (24h)*\n"
        msg += "━━━━━━━━━━━━━━━━\n"
        for i in range(min(5, len(usdt_pairs))):
            t = usdt_pairs[i]
            # Bybit pcnt is a decimal, e.g., 0.05 for 5%
            change = float(t['price24hPcnt']) * 100
            price = float(t['lastPrice'])
            msg += f"{i+1}. *{t['symbol'].replace('USDT', '')}*: +{change:.1f}% (`${price:,.2f}`)\n"
            
        return msg
    except Exception as e:
        print(f"❌ Top Gainers Exception: {e}")
        return "⚠️ Could not fetch market movers. Please try again."

def get_last_update_time():
    """Helper for UI timestamping"""
    import datetime
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S UTC")