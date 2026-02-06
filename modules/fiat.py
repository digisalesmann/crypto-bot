import os
from database import Wallet, Transaction, db

# Load Rates from Config
from modules.payment_methods import PAYMENT_METHODS
def get_rates(coin, fiat):
    """
    Returns the Admin-set buy and sell rates from .env
    Buy Rate: User sells crypto, receives fiat (what the desk pays)
    from modules.payment_methods import PAYMENT_METHODS
    Sell Rate: User buys crypto, pays fiat (what the desk charges)
    """
    buy_key = f"OTC_BUY_RATE_{coin}_{fiat}"
    sell_key = f"OTC_SELL_RATE_{coin}_{fiat}"
    buy_rate = os.getenv(buy_key)
    sell_rate = os.getenv(sell_key)
    return (
        float(buy_rate) if buy_rate else 0.0,
        float(sell_rate) if sell_rate else 0.0
    )
def list_fiat_methods():
    """
    Returns a list of all supported fiat/off-chain payment methods.
    """
    return [info['label'].lower() for info in PAYMENT_METHODS.values()]

def get_fiat_dashboard(user):
    """
    Shows the user's Fiat wallet and current Admin Rates.
    """

    # 1. Get Balances
    print(f"[DEBUG] get_fiat_dashboard called for user: {user}")
    fiat_currency = "NGN"  # Default local currency, or make dynamic
    total_crypto_usdt = 0.0
    fiat_bal = 0.0
    from services.coingecko_price import CoinGeckoPriceService
    cg_service = CoinGeckoPriceService()

    # Sum all crypto balances (excluding fiat)
    wallets = Wallet.select().where(Wallet.user == user)
    for w in wallets:
        if w.currency.upper() == fiat_currency:
            fiat_bal = w.balance
        else:
            total = w.balance + w.locked
            if w.currency.upper() == 'USDT':
                total_crypto_usdt += total
            else:
                try:
                    price = cg_service.get_price(w.currency.lower(), vs_currency="usdt")
                    if price:
                        total_crypto_usdt += total * float(price)
                except Exception:
                    pass

    # 2. Get Buy/Sell Rates
    buy_rate, sell_rate = get_rates("USDT", fiat_currency)

    dashboard = (
        "🏦 *OTC Trading Desk*\n"
        "━━━━━━━━━━━━━━━━\n"
        "Instant cash settlements. Zero fees.\n\n"
        f"💵 *Your Balance:*\n"
        f"• Crypto: `{total_crypto_usdt:,.2f} USDT`\n"
        f"• Fiat:   `{fiat_bal:,.2f} {fiat_currency}`\n\n"
        "📉 *Today's Rates:*\n"
        f"• Buy: *{buy_rate:,.2f} {fiat_currency}*\n"
        f"• Sell: *{sell_rate:,.2f} {fiat_currency}*\n\n"
        "🔄 *Actions:*\n"
        "• `swap USDT NGN 50` (Sell Crypto)\n"
        "• `withdraw NGN 50000 [Bank] [Acct]`"
    )
    print(f"[DEBUG] get_fiat_dashboard returning: {dashboard}")
    return dashboard

def get_fiat_deposit_info(method: str):
    """
    Returns instructions and details for a given fiat/off-chain payment method.
    """
    method = method.lower().replace(" ", "")
    # Accept both 'bank' and 'banktransfer' for bank deposit
    if method in ["banktransfer", "bank"]:
        info = PAYMENT_METHODS.get("bank")
    else:
        info = PAYMENT_METHODS.get(method)
    if not info:
        return f"⚠️ Unsupported payment method: {method}."
    return f"\U0001F4B5 *Deposit via {info['label']}*\n" \
           f"━━━━━━━━━━━━━━\n" \
           f"{info['instructions']}\n\n" \
           f"`{info['details']}`\n\n" \
           f"⚠️ *IMPORTANT:*\nInclude your User ID in the payment note or send a screenshot to Support."
    fiat_currency = "NGN" # Default local currency, or make dynamic
    def list_fiat_methods():
        """
        Returns a list of all supported fiat/off-chain payment methods.
        """
        return [info['label'] for info in PAYMENT_METHODS.values()]
    total_crypto_usdt = 0.0
    from services.coingecko_price import CoinGeckoPriceService
    cg_service = CoinGeckoPriceService()

    # Sum all crypto balances (excluding fiat)
    wallets = Wallet.select().where(Wallet.user == user)
    for w in wallets:
        if w.currency.upper() == fiat_currency:
            fiat_bal = w.balance
        else:
            total = w.balance + w.locked
            if w.currency.upper() == 'USDT':
                total_crypto_usdt += total
            else:
                try:
                    price = cg_service.get_price(w.currency.lower(), vs_currency="usdt")
                    if price:
                        total_crypto_usdt += total * float(price)
                except Exception:
                    pass

    # 2. Get Buy/Sell Rates
    buy_rate, sell_rate = get_rates("USDT", fiat_currency)

    dashboard = (
        "🏦 *OTC Trading Desk*\n"
        "━━━━━━━━━━━━━━━━\n"
        "Instant cash settlements. Zero fees.\n\n"
        f"💵 *Your Balance:*\n"
        f"• Crypto: `{total_crypto_usdt:,.2f} USDT`\n"
        f"• Fiat:   `{fiat_bal:,.2f} {fiat_currency}`\n\n"
        "📉 *Today's Rates:*\n"
        f"• Buy: *{buy_rate:,.2f} {fiat_currency}*\n"
        f"• Sell: *{sell_rate:,.2f} {fiat_currency}*\n\n"
        "🔄 *Actions:*\n"
        "• `swap USDT NGN 50` (Sell Crypto)\n"
        "• `withdraw NGN 50000 [Bank] [Acct]`"
    )
    print(f"[DEBUG] get_fiat_dashboard returning: {dashboard}")
    return dashboard

def execute_swap(user, msg):
    """
    Command: swap USDT NGN 50
    Logic: Deduct USDT -> Add NGN -> Record TX
    """
    try:
        parts = msg.split()
        if len(parts) != 4:
            return "⚠️ Usage: `swap [FROM] [TO] [AMOUNT]`\nEx: `swap USDT NGN 50`"
            
        coin = parts[1].upper()
        fiat = parts[2].upper()
        amount = float(parts[3])
        
        # 1. Validation
        if amount <= 0: return "⚠️ Amount must be positive."
        
        buy_rate, sell_rate = get_rates(coin, fiat)
        # For swap, assume user is selling crypto (use buy_rate)
        rate = buy_rate
        if rate == 0:
            return f"⚠️ Trading pair {coin}/{fiat} is currently closed."
        
        fiat_amount = amount * rate
        
        # 2. Check Balance
        try:
            coin_wallet = Wallet.get(Wallet.user == user, Wallet.currency == coin)
            if coin_wallet.balance < amount:
                return f"❌ Insufficient {coin}. Balance: {coin_wallet.balance}"
        except:
            return f"❌ You have no {coin} to swap."

        # 3. ATOMIC SWAP (The Exchange)
        with db.atomic():
            # A. Deduct Crypto
            coin_wallet.balance -= amount
            coin_wallet.save()
            
            # B. Add Fiat (Create wallet if missing)
            fiat_wallet, _ = Wallet.get_or_create(user=user, currency=fiat)
            fiat_wallet.balance += fiat_amount
            fiat_wallet.save()
            
            # C. Record Record
            Transaction.create(
                user=user,
                type='OTC_SWAP',
                currency=fiat,
                amount=fiat_amount,
                status='completed',
                tx_hash=f"Sold {amount} {coin} @ {rate}"
            )
            
        return (
            "✅ *Swap Successful*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🔻 Sold: `{amount} {coin}`\n"
            f"🟢 Received: `{fiat_amount:,.2f} {fiat}`\n"
            f"💳 New Fiat Balance: `{fiat_wallet.balance:,.2f} {fiat}`\n\n"
            "Type `withdraw [ASSET] [AMOUNT] [DESTINATION]` to cash out.\n"
            "Example: `withdraw BTC 0.01 bc1...` or `withdraw NGN 50000 0012345678_GTBank`"
        )

    except ValueError:
        return "⚠️ Invalid format."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"