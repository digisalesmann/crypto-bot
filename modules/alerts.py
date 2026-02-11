from modules import market
import state_manager
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
            return "⚠️ Usage: alert [Coin] [Price]\nEx: alert SOL 25.5"

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

        emoji = "📈" if condition == 'above' else "📉"
        return (
            f"🔔 *Strategic Alert Set*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"💎 *{symbol}*\n"
            f"🎯 Target: {target_price}\n"
            f"⚡ Current: {current_price}\n\n"
            f"{emoji} I will notify you when price *crosses {condition}* this level."
        )

    except ValueError:
        return "⚠️ Invalid price. Usage: alert SOL 20.5"
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
        msg += f"• *{a.symbol}*: {direction} ${a.target_price:,.2f}\n"
    
    return msg

def handle_alert_flow(user, msg, session):
    step = session.get('step', 1)
    cancel_words = ['cancel', 'exit', 'stop']
    
    if msg.lower() in cancel_words:
        return "❌ Alert setup cancelled.", session, True

    # STEP 1: Select Coin
    if step == 1:
        session['step'] = 2
        return "🔔 *Set Price Alert*\nWhich coin do you want to monitor? (e.g., BTC, SOL, ETH)", session, False

    # STEP 2: Input Target Price
    elif step == 2:
        coin = msg.strip().upper().replace("/", "")
        if not coin.endswith("USDT"): coin += "USDT"
        
        current_price = market.fetch_raw_price(coin)
        if not current_price:
            return f"⚠️ Could not find market data for {coin}. Please try another symbol.", session, False
            
        session['coin'] = coin
        session['current'] = current_price
        session['step'] = 3
        return (
            f"📈 *Current {coin}:* ${current_price:,.2f}\n\n"
            "At what price should I notify you? (Enter the numeric value):"
        ), session, False

    # STEP 3: Confirm Logic
    elif step == 3:
        try:
            target = float(msg.strip().replace(",", ""))
            session['target'] = target
            
            # Auto-detect direction
            direction = "above" if target > session['current'] else "below"
            session['direction'] = direction
            session['step'] = 4
            
            summary = (
                f"🚨 *Confirm Alert*\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"Coin: {session['coin']}\n"
                f"Notify when: *{direction}* ${target:,.2f}\n\n"
                "Type *YES* to activate."
            )
            return summary, session, False
        except ValueError:
            return "⚠️ Invalid amount. Please enter a number (e.g., 55000).", session, False

    # STEP 4: Save and Close
    elif step == 4:
        if 'yes' in msg.lower():
            # DB Logic: Alert.create(user=user, symbol=session['coin'], target_price=session['target'], condition=session['direction'])
            Alert.create(user=user, symbol=session['coin'], target_price=session['target'], condition=session['direction'], is_active=True)
            return f"✅ Alert activated! I'll ping you when {session['coin']} hits ${session['target']:,.2f}.", session, True
        return "❌ Alert cancelled.", session, True