import os
import config
from modules import market as market_service

def get_fiat_dashboard(user):
    """
    Returns a professional dashboard of today's exchange rates.
    """
    # 1. Fetch Admin-set OTC Rates from Env
    # In production, these can also be fetched from a 'Settings' table in your DB
    usdt_ngn_buy = float(os.getenv("OTC_BUY_RATE_USDT_NGN", 1550.00))
    usdt_ngn_sell = float(os.getenv("OTC_SELL_RATE_USDT_NGN", 1600.00))
    
    # 2. Get Live Global Market Price (for comparison)
    global_btc = market_service.fetch_raw_price("BTC")
    
    msg = (
        "💱 *PPAY OTC & P2P DESK*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"*Date:* {market_service.get_last_update_time()}\n\n"
        "💳 *USDT/NGN RATES*\n"
        "────────────────\n"
        f"🟢 *We Buy:* `₦{usdt_ngn_buy:,.2f}`\n"
        f"🔴 *We Sell:* `₦{usdt_ngn_sell:,.2f}`\n\n"
        "📊 *GLOBAL MARKET (REF)*\n"
        "────────────────\n"
        f"₿ BTC/USDT: `${global_btc:,.2f}`\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "💡 *How to Trade:*\n"
        "• Type `swap` to start an instant conversion.\n"
        "• Type `deposit bank` to fund your NGN wallet."
    )
    return msg

def get_rates(from_asset, to_asset):
    """
    Helper to fetch specific rates for the Swap flow.
    """
    pair = f"{from_asset}_{to_asset}".upper()
    
    # Logic for USDT <-> NGN
    if pair == "USDT_NGN":
        return float(os.getenv("OTC_BUY_RATE_USDT_NGN", 1550.00))
    elif pair == "NGN_USDT":
        # Using 1/SellRate for the math conversion
        sell_rate = float(os.getenv("OTC_SELL_RATE_USDT_NGN", 1600.00))
        return 1 / sell_rate if sell_rate > 0 else 0
        
    return None