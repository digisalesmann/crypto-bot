import database
from database import db, User, Wallet, Transaction
import services.exchange as cex # Your wrapper for price checking

def execute_buy(user, symbol, amount_usdt):
    # 1. Get Price
    # symbol = "BTC/USDT"
    current_price = cex.get_price(symbol)
    
    # 2. Check Balance (Internal DB)
    usdt_wallet = Wallet.get_or_create(user=user, currency='USDT')[0]
    
    if usdt_wallet.balance < amount_usdt:
        return "❌ Insufficient USDT Balance."

    # 3. Calculate Asset Amount
    # We can add a "Spread" fee here (Your profit!)
    # Real price: 90000. User price: 90500 (You make the difference)
    spread = 1.01 # 1% fee
    execution_price = current_price * spread
    asset_amount = amount_usdt / execution_price
    asset_coin = symbol.split('/')[0] # BTC

    # 4. EXECUTE (Update DB Ledger)
    with db.atomic(): # Transaction safety
        # Deduct USDT
        usdt_wallet.balance -= amount_usdt
        usdt_wallet.save()
        
        # Add BTC
        btc_wallet = Wallet.get_or_create(user=user, currency=asset_coin)[0]
        btc_wallet.balance += asset_amount
        btc_wallet.save()
        
        # Record Transaction
        Transaction.create(user=user, type='BUY', currency=asset_coin, amount=asset_amount, status='completed')

    # 5. (Optional) HEDGE
    # Automatically buy on real Bybit so you are not "short" on Bitcoin
    # cex.execute_market_buy(symbol, amount_usdt)

    return f"✅ SUCCESS!\nBought {asset_amount:.6f} {asset_coin}\nPrice: ${execution_price:.2f}"