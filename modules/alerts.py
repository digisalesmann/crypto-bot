from database import Alert
from modules import market

def create_alert(user, msg):
    """
    Saves a strategic price alert.
    Auto-corrects 'SOL' to 'SOLUSDT'.
    """
    try:
        # 1. Parse Input: "alert SOL 150"
        parts = msg.split()
        if len(parts) < 3:
            return "⚠️ Usage: `alert [Coin] [Price]`\nEx: `alert SOL 25.5`"

        # 2. Format Symbol (Auto-add USDT if missing)
        raw_symbol = parts[1].upper()
        symbol = raw_symbol if "USDT" in raw_symbol else f"{raw_symbol}USDT"
        
        # 3. Clean Price
        target_str = parts[2].replace('$', '').replace(',', '')
        target_price = float(target_str)

        # 4. Get Current Price (to decide if we are waiting for a PUMP or DUMP)
        current_price = market.fetch_raw_price(symbol)
        
        if not current_price:
             return f"⚠️ I can't find *{symbol}* on Bybit. Check the name."

        # 5. Determine Strategic Direction
        # If Target > Current, we are waiting for a CROSS UP (Bullish)
        # If Target < Current, we are waiting for a CROSS DOWN (Bearish)
        condition = 'above' if target_price > current_price else 'below'

        # 6. Save to Database
        Alert.create(
            user=user,
            symbol=symbol,
            target_price=target_price,
            condition=condition
        )

        emoji = "📈" if condition == 'above' else "zz📉"
        return (
            f"🔔 *Strategic Alert Set*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"💎 *{symbol}*\n"
            f"🎯 Target: `{target_price}`\n"
            f"⚡ Current: `{current_price}`\n\n"
            f"{emoji} I will notify you when price *crosses {condition}* this level."
        )

    except ValueError:
        return "⚠️ Invalid price. Usage: `alert SOL 20.5`"
    except Exception as e:
        return f"⚠️ System Error: {str(e)}"

def get_my_alerts(user):
    """List active alerts"""
    alerts = Alert.select().where(Alert.user == user, Alert.is_active == True)
    
    if not alerts:
        return "🔕 No active strategy alerts."
    
    msg = "🔔 *Active Strategy Alerts*\n━━━━━━━━━━━━━━━━\n"
    for a in alerts:
        direction = "Upper Limit" if a.condition == 'above' else "Lower Limit"
        msg += f"• *{a.symbol}*: {direction} `${a.target_price:,.2f}`\n"
    
    return msg