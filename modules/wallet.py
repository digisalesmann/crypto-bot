import os
from database import Wallet, Transaction, db
from modules import notifications

def get_fee_tier(kyc_level):
    """
    Returns the trading fee rates based on user KYC level.
    """
    if kyc_level >= 3:
        return "🏆 VIP 1 (0.04% / 0.06%)"
    elif kyc_level == 2:
        return "⭐ Pro (0.06% / 0.08%)"
    else:
        return "👤 Standard (0.1% / 0.1%)"

def handle_balance(user):
    """
    Generates a detailed Account Overview:
    - KYC Status & ID
    - Fee Tier
    - Detailed Asset List (Crypto vs Fiat)
    - Estimates total value in USDT for all crypto assets
    """
    print(f"[DEBUG] handle_balance called for user: {user}")

    try:
        # 1. Fetch all non-zero wallets for this user (force evaluation to list)
        print("[DEBUG] Step 1: Fetching wallets...")
        wallets_query = Wallet.select().where(
            Wallet.user == user, 
            (Wallet.balance > 0) | (Wallet.locked > 0)
        )
        wallets = list(wallets_query)
        print(f"[DEBUG] Wallets found: {len(wallets)} wallets")

        # 2. Header Information
        print("[DEBUG] Step 2: Building header...")
        fee_tier = get_fee_tier(user.kyc_level)
        status_emoji = "🟢" if user.kyc_level > 1 else "🟡"

        msg = (
            "📊 *ACCOUNT OVERVIEW*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 *User ID:* `{getattr(user, 'id', 'N/A')}`\n"
            f"🛡️ *Status:* {status_emoji} Level {getattr(user, 'kyc_level', 'N/A')} (Verified)\n"
            f"⚡ *Fee Tier:* {fee_tier}\n\n"
            "💰 *ASSET BALANCES*\n"
            "────────────────\n"
        )

        # 3. Asset Loop
        if not wallets:
            msg += "_(No assets found)_\n"
            print("[DEBUG] No wallets found for user.")
        else:
            print("[DEBUG] Step 3: Processing wallets...")
            # Initialize price services with error handling - IMPORT LOCALLY
            cg_service = None
            price_cache = None
            
            try:
                print("[DEBUG] Step 3a: Importing CoinGeckoPriceService...")
                from services.coingecko_price import CoinGeckoPriceService
                cg_service = CoinGeckoPriceService()
                print("[DEBUG] Step 3b: CoinGeckoPriceService initialized successfully")
            except Exception as e:
                print(f"[DEBUG] Error initializing CoinGeckoPriceService: {e}")
                cg_service = None
            
            # DON'T USE PriceCache - it has threading issues
            # Just use direct API calls with the service
            
            total_est_usdt = 0.0

            for idx, wallet_obj in enumerate(wallets):
                print(f"[DEBUG] Step 4.{idx}: Processing wallet {idx+1}/{len(wallets)}")
                
                try:
                    # Safely get wallet attributes
                    currency = getattr(wallet_obj, 'currency', 'UNKNOWN')
                    balance = float(getattr(wallet_obj, 'balance', 0.0))
                    locked = float(getattr(wallet_obj, 'locked', 0.0))
                    wallet_id = getattr(wallet_obj, 'id', 'N/A')
                    
                    print(f"[DEBUG] Wallet {wallet_id}: {currency} - balance={balance}, locked={locked}")
                    
                    # Calculate Total (Available + Locked)
                    total = balance + locked

                    # Formatting
                    msg += f"💎 *{currency}*\n"
                    msg += f"   • Avail: `{balance:,.6f}`\n"

                    if locked > 0:
                        msg += f"   • Locked: `{locked:,.6f}` 🔒\n"

                    # Estimate value in USDT for all assets
                    est = None
                    if currency == "USDT":
                        est = total
                        total_est_usdt += est
                        print(f"[DEBUG] USDT asset, value added: {est}")
                    else:
                        price = None
                        
                        # Use direct API call for price (no cache)
                        if currency != "NGN" and cg_service:
                            try:
                                print(f"[DEBUG] Getting price for {currency}...")
                                price = cg_service.get_price(currency.lower(), vs_currency="usdt")
                                print(f"[DEBUG] Price for {currency}: {price}")
                            except Exception as e:
                                print(f"[DEBUG] Exception getting price for {currency}: {e}")
                                price = None
                        
                        # Special handling for NGN (use sell rate for USDT to NGN conversion)
                        if currency == "NGN" and not price:
                            try:
                                ngn_sell_rate_env = os.getenv("OTC_SELL_RATE_USDT_NGN")
                                if ngn_sell_rate_env:
                                    NGN_USDT_SELL_RATE = float(ngn_sell_rate_env)
                                    price = 1.0 / NGN_USDT_SELL_RATE
                                    print(f"[DEBUG] Using env NGN/USDT SELL rate: {NGN_USDT_SELL_RATE}, price: {price}")
                                else:
                                    NGN_USDT_SELL_RATE = 1600.0
                                    price = 1.0 / NGN_USDT_SELL_RATE
                                    print(f"[DEBUG] Using default NGN/USDT SELL rate: {NGN_USDT_SELL_RATE}, price: {price}")
                            except Exception as e:
                                print(f"[DEBUG] Error reading NGN/USDT SELL rate from env: {e}")
                                price = None

                        if price:
                            try:
                                est = total * float(price)
                                msg += f"   • ≈ `{est:,.2f} USDT`\n"
                                total_est_usdt += est
                                print(f"[DEBUG] {currency} asset, value added: {est}")
                            except Exception as e:
                                print(f"[DEBUG] Error calculating est for {currency}: {e}")
                                msg += f"   • ≈ `N/A USDT` (Calc Error)\n"
                        else:
                            msg += f"   • ≈ `N/A USDT` (No price)\n"
                            print(f"[DEBUG] No price for {currency}, skipped in total.")
                            
                except Exception as wallet_error:
                    print(f"[ERROR] Exception processing wallet {idx}: {wallet_error}")
                    import traceback
                    traceback.print_exc()
                    # Continue to next wallet instead of crashing
                    continue

            msg += "────────────────\n"
            msg += f"💵 *Est. Total (USDT):* `${total_est_usdt:,.2f}`\n"
            print(f"[DEBUG] Total estimated USDT: {total_est_usdt}")

        # 4. Action Buttons (Text based)
        msg += "\n*ACTIONS:*\n"
        msg += "Type `deposit [COIN] [CHAIN]` to add funds\n"
        msg += "Type `swap [FROM] [TO] [AMOUNT]` to convert\n"

        print(f"[DEBUG] handle_balance returning successfully")
        return msg
        
    except Exception as e:
        print(f"[CRITICAL] handle_balance fatal error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return "⚠️ System error fetching balance. Please contact support."

def get_deposit_address(user):
    """
    Returns a generic multi-asset deposit info message, not just USDT.
    """
    from modules.bybit_client import SUPPORTED_COINS, SUPPORTED_CHAINS
    coins = ', '.join(SUPPORTED_COINS)
    chains = ', '.join(sorted({c for v in SUPPORTED_CHAINS.values() for c in v}))
    return (
        f"\U0001F3E6 *Deposit Crypto*\n"
        "━━━━━━━━━━━━━━\n"
        "Send supported coins to your CEX Master Wallet.\n\n"
        f"*Supported Coins:* {coins}\n"
        f"*Supported Chains:* {chains}\n\n"
        "Type `deposit [COIN] [CHAIN]` for a specific address.\n"
        "Example: `deposit BTC BTC` or `deposit USDT TRC20`\n"
        "\n⚠️ *IMPORTANT:*\n"
        f"Please include your User ID (*{user.id}*) in the transaction memo or send a screenshot to Support.\n"
        "Funds will be credited after 1 confirmation."
    )

def get_deposit_address_dynamic(user, coin=None, chain=None):
    """
    Returns a deposit address for a specific coin and chain, or generic info if not provided.
    """
    if coin and chain:
        from modules.bybit_client import get_deposit_address, SUPPORTED_COINS, SUPPORTED_CHAINS
        coin = coin.upper()
        chain = chain.upper()
        if coin not in SUPPORTED_COINS:
            return f"⚠️ {coin} is not supported. Supported: {', '.join(SUPPORTED_COINS)}"
        if chain not in SUPPORTED_CHAINS.get(coin, []):
            return f"⚠️ {chain} is not supported for {coin}. Supported: {', '.join(SUPPORTED_CHAINS.get(coin, []))}"
        address = get_deposit_address(coin, chain)
        if address:
            return (
                f"\U0001F3E6 *Deposit {coin} ({chain})*\n"
                "━━━━━━━━━━━━━━\n"
                f"Send only {coin} via {chain} to:\n\n"
                f"`{address}`\n\n"
                "⚠️ *IMPORTANT:*\n"
                f"Include your User ID (*{user.id}*) in the memo or send a screenshot to Support.\n"
                "Funds will be credited after 1 confirmation."
            )
        else:
            return f"⚠️ No deposit address available for {coin} on {chain}."
    else:
        return get_deposit_address(user)

def get_withdrawal_fees(coin):
    """Returns the network fee for withdrawals."""
    # Crypto Network Fees
    if coin == "USDT": return 1.0  # TRC20 Fee
    if coin == "BTC": return 0.0005
    if coin == "ETH": return 0.005
    # Fiat (Bank Transfer) Fees - Set to 0.0 for free withdrawals
    return 0.0

def handle_withdrawal(user, msg):
    """
    Parses: withdraw [COIN/FIAT] [AMOUNT] [DESTINATION]
    Logic: Checks balance -> Deducts funds -> Creates Pending Transaction
    """
    try:
        parts = msg.split()
        if len(parts) < 4:
            return (
                "⚠️ *Withdrawal Error*\n"
                "Usage: `withdraw [ASSET] [AMOUNT] [DESTINATION]`\n\n"
                "*Examples:*\n"
                "• Crypto: `withdraw BTC 0.01 bc1...`, `withdraw USDT 100 T9yD14...`\n"
                "• Fiat: `withdraw NGN 50000 0012345678_GTBank`"
            )

        coin = parts[1].upper()
        amount = float(parts[2])
        # Join all remaining parts as the destination (e.g., "0012... GT Bank")
        destination = " ".join(parts[3:])
        
        # 1. Validation
        if amount <= 0:
            return "⚠️ Amount must be positive."
            
        # Determine Fee & Label based on Asset Type
        if coin in ['USDT', 'BTC', 'ETH', 'SOL']:
            fee = get_withdrawal_fees(coin)
            dest_label = "Address"
        else:
            # Assume it is Fiat (NGN, EUR, BRL, etc.)
            fee = 0.0 # Zero fee for bank transfers (or change this)
            dest_label = "Bank Details"

        total_deduction = amount + fee

        # 2. Check Wallet Balance
        try:
            user_wallet = Wallet.get(Wallet.user == user, Wallet.currency == coin)
        except:
            return f"⚠️ You do not have a {coin} wallet yet."

        if user_wallet.balance < total_deduction:
            return (
                f"❌ *Insufficient Funds*\n"
                f"Balance: `{user_wallet.balance:,.2f}` {coin}\n"
                f"Required: `{total_deduction:,.2f}` {coin} (incl {fee} fee)"
            )

        # 3. ATOMIC TRANSACTION (Safe DB Update)
        with db.atomic():
            # Deduct from Balance
            user_wallet.balance -= total_deduction
            user_wallet.save()
            
            # Create Transaction Record
            tx = Transaction.create(
                user=user,
                type='WITHDRAWAL',
                currency=coin,
                amount=amount,
                status='pending', # Waiting for Admin processing
                tx_hash=destination # Storing the dest address/bank details here
            )

        return (
            "⏳ *Withdrawal Requested*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 TX ID: `{tx.id}`\n"
            f"💰 Amount: `{amount:,.2f} {coin}`\n"
            f"💸 Fee: `{fee} {coin}`\n"
            f"📍 {dest_label}: `{destination}`\n\n"
            "Status: *Pending Review*\n"
            "You will be notified once processed."
        )

    except ValueError:
        return "⚠️ Invalid amount format."
    except Exception as e:
        return f"⚠️ System Error: {str(e)}"

def handle_internal_transfer(sender, msg):
    """
    Command: transfer [COIN] [AMOUNT] [TO_PHONE]
    Transfers asset from sender to another user (by phone), production ready.
    """
    from database import User, Wallet, Transaction, db
    try:
        parts = msg.split()
        if len(parts) != 4:
            return (
                "⚠️ *Transfer Error*\n"
                "Usage: `transfer [COIN] [AMOUNT] [TO_PHONE]`\n"
                "Example: `transfer USDT 10 +2348012345678`"
            )
        coin = parts[1].upper()
        amount = float(parts[2])
        to_phone = parts[3].strip()
        if amount <= 0:
            return "⚠️ Amount must be positive."
        # 1. Validate recipient
        recipient = User.get_or_none(User.phone == to_phone)
        if not recipient:
            return f"⚠️ Recipient with phone {to_phone} not found."
        if recipient.id == sender.id:
            return "⚠️ You cannot transfer to yourself."
        # 2. Check sender balance
        try:
            sender_wallet = Wallet.get(Wallet.user == sender, Wallet.currency == coin)
        except:
            return f"⚠️ You do not have a {coin} wallet."
        if sender_wallet.balance < amount:
            return f"❌ Insufficient {coin} balance."
        # 3. Transfer (atomic)
        with db.atomic():
            sender_wallet.balance -= amount
            sender_wallet.save()
            recipient_wallet, _ = Wallet.get_or_create(user=recipient, currency=coin)
            recipient_wallet.balance += amount
            recipient_wallet.save()
            # Record transactions for both users
            Transaction.create(user=sender, type='TRANSFER_OUT', currency=coin, amount=amount, status='completed', tx_hash=f"To {to_phone}")
            Transaction.create(user=recipient, type='TRANSFER_IN', currency=coin, amount=amount, status='completed', tx_hash=f"From {sender.phone}")
            # Notify both parties
            notifications.send_internal_transfer_notification(sender, amount, coin, 'sent', to_phone)
            notifications.send_internal_transfer_notification(recipient, amount, coin, 'received', sender.phone)
        return (
            f"✅ *Transfer Successful!*\n"
            f"Sent: `{amount} {coin}` to {to_phone}\n"
            f"New Balance: `{sender_wallet.balance:,.6f} {coin}`"
        )
    except ValueError:
        return "⚠️ Invalid amount format."
    except Exception as e:
        return f"⚠️ System Error: {str(e)}"

def get_tx_history(user):
    """Shows the last 5 transactions (Deposits/Withdrawals/Swaps)"""
    txs = Transaction.select().where(Transaction.user == user).order_by(Transaction.timestamp.desc()).limit(5)
    
    if not txs:
        return "📭 No transaction history found."
    
    msg = "📜 *Transaction History*\n━━━━━━━━━━━━━━━━\n"
    for t in txs:
        # Determine Emoji
        if t.type == 'DEPOSIT': emoji = "🟢"
        elif t.type == 'WITHDRAWAL': emoji = "🔴"
        elif t.type == 'OTC_SWAP': emoji = "🔄"
        else: emoji = "⚪"
        
        date = t.timestamp.strftime("%Y-%m-%d")
        
        msg += f"{emoji} *{t.type}* ({t.status})\n"
        msg += f"   {t.amount:,.2f} {t.currency} • {date}\n"
        
    return msg