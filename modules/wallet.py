import os
from database import Wallet, Transaction, db, User
from modules import notifications
import config

# --- SESSION HELPERS ---

def start_withdraw_session(user):
    return {'step': 0, 'mode': None, 'asset': None, 'network': None, 'amount': None, 'account_number': None, 'bank_name': None, 'account_name': None, 'destination': None}

def handle_withdraw_flow(user, msg, session):
    # Block if account is frozen
    if getattr(user, 'is_frozen', False):
        return ("❄️ Your account is currently frozen. Withdrawals are disabled. Contact support to unfreeze.", session, True)
    cancel_words = ['cancel', 'abort', 'exit', 'stop']
    if msg.strip().lower() in cancel_words:
        return ("❌ Withdrawal process cancelled. Type `withdraw` to restart.", session, True)


    if session['step'] == 0:
        session['step'] = 1
        return ("💸 *Withdrawal Request*\nWould you like to withdraw *crypto* or *fiat*?", session, False)

    elif session['step'] == 1:
        mode = msg.strip().lower()
        if mode in ['crypto', '1']:
            session['mode'] = 'crypto'
            session['step'] = 2
            return ("Which crypto asset do you want to withdraw? (USDT, BTC, ETH, SOL)", session, False)
        elif mode in ['fiat', '2', 'ngn']:
            session['mode'] = 'fiat'
            session['step'] = 10
            return ("How much NGN do you want to withdraw?", session, False)
        else:
            return ("Please reply with 'crypto' or 'fiat' to continue.", session, False)

    # --- Crypto Withdraw Flow ---

    elif session['step'] == 2 and session.get('mode') == 'crypto':
        asset = msg.strip().upper()
        session['asset'] = asset
        session['step'] = 2.5
        # Suggest common networks for each asset
        networks = {
            'USDT': 'ERC20, TRC20, BEP20',
            'BTC': 'BTC',
            'ETH': 'ERC20',
            'SOL': 'SOL',
        }
        network_options = networks.get(asset, 'ERC20, TRC20, BEP20')
        return (f"Which network do you want to use for {asset}? (e.g., {network_options})", session, False)

    elif session['step'] == 2.5 and session.get('mode') == 'crypto':
        network = msg.strip().upper()
        session['network'] = network
        session['step'] = 3
        return (f"How much {session['asset']} do you want to withdraw on {network}?", session, False)


    elif session['step'] == 3 and session.get('mode') == 'crypto':
        try:
            amount = float(msg.strip())
            if amount <= 0: return ("❌ Amount must be positive.", session, False)
            session['amount'] = amount
            session['step'] = 4
            return (f"Enter the {session['asset']} withdrawal address on {session['network']}:", session, False)
        except ValueError:
            return ("❌ Please enter a valid numeric amount.", session, False)

    elif session['step'] == 4 and session.get('mode') == 'crypto':
        dest = msg.strip()
        session['destination'] = dest
        session['step'] = 4.5
        return ("🔒 Please enter your 4-digit PIN to confirm this withdrawal:", session, False)

    elif session['step'] == 4.5 and session.get('mode') == 'crypto':
        pin = msg.strip()
        if not (pin.isdigit() and len(pin) == 4):
            return ("❌ PIN must be exactly 4 digits. Please enter your 4-digit PIN:", session, False)
        if user.pin != pin:
            return ("❌ Incorrect PIN. Please try again:", session, False)
        coin = session['asset']
        network = session['network']
        amount = session['amount']
        dest = session['destination']
        # Calculate Fees
        fee = 1.0 if coin == "USDT" else (0.0005 if coin == "BTC" else 0.0)
        total_deduction = amount + fee
        try:
            user_wallet = Wallet.get(Wallet.user == user, Wallet.currency == coin)
            if user_wallet.balance < total_deduction:
                return (f"❌ *Insufficient Funds*\nBalance: `{user_wallet.balance:,.2f}` {coin}\nRequired: `{total_deduction:,.2f}`", session, True)
            with db.atomic():
                user_wallet.balance -= total_deduction
                user_wallet.save()
                tx = Transaction.create(
                    user=user, type='WITHDRAWAL', currency=coin, 
                    amount=amount, status='pending', tx_hash=dest
                )
            # Trigger referral bonus payout if eligible
            from database import trigger_referral_payout
            trigger_referral_payout(user)
            # Notify Admin
            admin_msg = f"🚨 *NEW WITHDRAWAL*\nUser: {user.phone}\nAmt: {amount} {coin}\nNetwork: {network}\nDest: {dest}"
            notifications.send_push(type('Admin', (), {'phone': config.OWNER_PHONE.split(',')[0]}), admin_msg)
            return (f"⏳ *Withdrawal Requested*\nID: `{tx.id}`\nAmount: `{amount} {coin}`\nNetwork: {network}\nStatus: *Pending Review*", session, True)
        except Wallet.DoesNotExist:
            return (f"⚠️ You don't have a {coin} wallet.", session, True)

    # --- Fiat Withdraw Flow ---
    elif session['step'] == 10 and session.get('mode') == 'fiat':
        try:
            amount = float(msg.strip())
            if amount <= 0: return ("❌ Amount must be positive.", session, False)
            session['amount'] = amount
            session['step'] = 11
            return ("Enter your Account Number:", session, False)
        except ValueError:
            return ("❌ Please enter a valid numeric amount.", session, False)

    elif session['step'] == 11 and session.get('mode') == 'fiat':
        acct_num = msg.strip()
        if not acct_num.isdigit() or len(acct_num) < 8:
            return ("❌ Please enter a valid account number.", session, False)
        session['account_number'] = acct_num
        session['step'] = 12
        return ("Enter your Bank Name (e.g., GTBank):", session, False)

    elif session['step'] == 12 and session.get('mode') == 'fiat':
        bank_name = msg.strip()
        if not bank_name or len(bank_name) < 2:
            return ("❌ Please enter a valid bank name.", session, False)
        session['bank_name'] = bank_name
        session['step'] = 13
        return ("Enter your Account Name (as registered with your bank):", session, False)

    elif session['step'] == 13 and session.get('mode') == 'fiat':
        acct_name = msg.strip()
        if not acct_name or len(acct_name) < 2:
            return ("❌ Please enter a valid account name.", session, False)
        session['account_name'] = acct_name
        session['step'] = 13.5
        # Compose destination string for record
        session['destination'] = f"{session['account_number']} | {session['bank_name']} | {session['account_name']}"
        return ("🔒 Please enter your 4-digit PIN to confirm this withdrawal:", session, False)

    elif session['step'] == 13.5 and session.get('mode') == 'fiat':
        pin = msg.strip()
        if not (pin.isdigit() and len(pin) == 4):
            return ("❌ PIN must be exactly 4 digits. Please enter your 4-digit PIN:", session, False)
        if user.pin != pin:
            return ("❌ Incorrect PIN. Please try again:", session, False)
        coin = 'NGN'
        amount = session['amount']
        fee = 0.0
        total_deduction = amount + fee
        try:
            user_wallet = Wallet.get(Wallet.user == user, Wallet.currency == coin)
            if user_wallet.balance < total_deduction:
                return (f"❌ *Insufficient Funds*\nBalance: `{user_wallet.balance:,.2f}` {coin}\nRequired: `{total_deduction:,.2f}`", session, True)
            with db.atomic():
                user_wallet.balance -= total_deduction
                user_wallet.save()
                tx = Transaction.create(
                    user=user, type='WITHDRAWAL', currency=coin, 
                    amount=amount, status='pending', tx_hash=session['destination']
                )
            # Trigger referral bonus payout if eligible
            from database import trigger_referral_payout
            trigger_referral_payout(user)
            # Notify Admin
            admin_msg = f"🚨 *NEW FIAT WITHDRAWAL*\nUser: {user.phone}\nAmt: {amount} {coin}\nBank: {session['bank_name']}\nAcct No: {session['account_number']}\nAcct Name: {session['account_name']}"
            notifications.send_push(type('Admin', (), {'phone': config.OWNER_PHONE.split(',')[0]}), admin_msg)
            return (f"⏳ *Fiat Withdrawal Requested*\nID: `{tx.id}`\nAmount: `{amount} {coin}`\nBank: {session['bank_name']}\nAcct No: {session['account_number']}\nAcct Name: {session['account_name']}\nStatus: *Pending Review*", session, True)
        except Wallet.DoesNotExist:
            return (f"⚠️ You don't have a {coin} wallet.", session, True)

    # --- Transfer Flow ---
    elif session['step'] == 14 and session.get('mode') == 'crypto':
        recipient_phone = msg.strip()
        session['recipient'] = recipient_phone
        session['step'] = 15
        return f"How much {session['asset']} do you want to transfer?", session, False
    elif session['step'] == 15:
        try:
            amount = float(msg.strip())
            if amount <= 0:
                return "❌ Amount must be positive.", session, False
            session['amount'] = amount
            session['step'] = 16
            return "Type YES to confirm and send, or CANCEL to abort.", session, False
        except ValueError:
            return "❌ Please enter a valid numeric amount.", session, False
    elif session['step'] == 16:
        if msg.lower() == 'yes':
            asset = session['asset']
            amount = session['amount']
            recipient_phone = session['recipient']
            try:
                sender_wallet = Wallet.get(Wallet.user == user, Wallet.currency == asset)
                # Normalize phone number to support both formats
                def normalize_phone(phone):
                    phone = phone.strip()
                    if phone.startswith('+234'):
                        return phone
                    if phone.startswith('0') and len(phone) == 11:
                        return '+234' + phone[1:]
                    return phone
                norm_phone = normalize_phone(recipient_phone)
                try:
                    recipient_user = User.get((User.phone == recipient_phone) | (User.phone == norm_phone))
                except User.DoesNotExist:
                    return "⚠️ Recipient not found. Please check the phone number or invite them to register.", session, True
                recipient_wallet = Wallet.get(Wallet.user == recipient_user, Wallet.currency == asset)
                if sender_wallet.balance < amount:
                    return f"❌ Insufficient funds. Balance: {sender_wallet.balance:,.4f} {asset}", session, True
                # ...existing code...
                # ...existing code...
                with db.atomic():
                    sender_wallet.balance -= amount
                    sender_wallet.save()
                    recipient_wallet.balance += amount
                    recipient_wallet.save()
                    Transaction.create(user=user, type='TRANSFER', currency=asset, amount=amount, status='completed', tx_hash=recipient_phone)
                    Transaction.create(user=recipient_user, type='RECEIVE', currency=asset, amount=amount, status='completed', tx_hash=user.phone)
                # Trigger referral bonus payout if eligible
                from database import trigger_referral_payout
                trigger_referral_payout(user)
                admin_msg = f"🔁 *Internal Transfer*\nSender: {user.phone}\nRecipient: {recipient_user.phone}\nAsset: {asset}\nAmount: {amount}"
                notifications.send_push(type('Admin', (), {'phone': config.OWNER_PHONE.split(',')[0]}), admin_msg)
                return f"✅ Transfer of {amount} {asset} to {recipient_phone} completed.", session, True
            except Wallet.DoesNotExist:
                return f"❌ Wallet not found for asset {asset} or recipient.", session, True
        else:
            return "❌ Transfer aborted.", session, True
    return "❓ Unknown step. Type `menu`.", session, True

# --- CORE LOGIC ---

def handle_balance(user):
    wallets = Wallet.select().where(Wallet.user == user)
    if not wallets:
        return "💼 No wallets found."
    # Icon map for popular assets
    lines = [
        "💼 *WALLET OVERVIEW*",
        "━━━━━━━━━━━━━━"
    ]
    for w in wallets:
        lines.append(f"• {w.currency}: `{w.balance:,.4f}`")
    lines.append("\n━━━━━━━━━━━━━━")
    lines.append("Tip: Use 'swap', 'deposit', or 'withdraw' to manage your funds.")
    return "\n".join(lines)

def get_tx_history(user):
    """
    Returns a professional, high-density transaction history UI.
    """
    # Fetch last 5 transactions
    txs = Transaction.select().where(Transaction.user == user).order_by(Transaction.timestamp.desc()).limit(5)
    
    if not txs:
        return "📝 *TRANSACTION HISTORY*\n━━━━━━━━━━━━━━━━\nNo transactions recorded yet."

    # Header with Branded Divider
    lines = ["📊 *TRANSACTION HISTORY*", "━━━━━━━━━━━━━━━━\n"]

    for tx in txs:
        # 1. Status Emoji & Direction logic
        status_icon = "✅" if tx.status == 'completed' else "⏳" if tx.status == 'pending' else "❌"
        
        # 2. Type and Asset Branding
        asset_emoji = "🇳🇬" if tx.currency == "NGN" else "🪙"
        tx_type = tx.type.replace("_", " ").title()
        
        # 3. Format Timestamp (e.g., Feb 09, 19:30)
        dt = tx.timestamp.strftime("%b %d, %H:%M")

        # 4. Entry UI Construction
        lines.append(f"{status_icon} *{tx_type}* — `{dt}`")
        lines.append(f"┗ {asset_emoji} `{tx.amount:,.2f} {tx.currency}`")
        
        # 5. Add Reference/Hash if it exists (monospaced for easy copy)
        if tx.tx_hash and len(tx.tx_hash) > 2:
            # Show truncated hash/ref for clean look
            ref = tx.tx_hash[:15] + "..." if len(tx.tx_hash) > 18 else tx.tx_hash
            lines.append(f"   📎 Ref: `{ref}`")
            
        lines.append("────────────────") # Light separator between items

    # Footer
    lines.append(f"\n💡 *Quick Actions:*")
    lines.append("• Type `deposit` to add funds")
    lines.append("• Type `withdraw` to cash out")
    
    return "\n".join(lines)

def handle_transfer_flow(user, msg, session):
    # Block if account is frozen
    if getattr(user, 'is_frozen', False):
        return ("❄️ Your account is currently frozen. Transfers are disabled. Contact support to unfreeze.", session, True)
    step = session.get('step', 1)
    cancel_words = ['cancel', 'exit', 'stop', 'abort']
    if msg.lower() in cancel_words:
        return "❌ Transfer cancelled. Type `menu` to restart.", session, True

    if step == 1:
        session['step'] = 2
        return "Which asset do you want to transfer? (e.g., USDT, BTC, NGN)", session, False
    elif step == 2:
        session['asset'] = msg.strip().upper()
        session['step'] = 3
        return "Enter recipient's phone number:", session, False
    elif step == 3:
        session['recipient'] = msg.strip()
        session['step'] = 4
        return f"How much {session['asset']} do you want to transfer?", session, False
    elif step == 4:
        try:
            amount = float(msg.strip())
            if amount <= 0:
                return "❌ Amount must be positive.", session, False
            session['amount'] = amount
            session['step'] = 5
            return "Type YES to confirm and send, or CANCEL to abort.", session, False
        except ValueError:
            return "❌ Please enter a valid numeric amount.", session, False
    elif step == 5:
        if msg.lower() == 'yes':
            asset = session['asset']
            amount = session['amount']
            recipient_phone = session['recipient']
            try:
                sender_wallet = Wallet.get(Wallet.user == user, Wallet.currency == asset)
                # Normalize phone number to support both formats
                def normalize_phone(phone):
                    phone = phone.strip()
                    if phone.startswith('+234'):
                        return phone
                    if phone.startswith('0') and len(phone) == 11:
                        return '+234' + phone[1:]
                    return phone
                norm_phone = normalize_phone(recipient_phone)
                try:
                    recipient_user = User.get((User.phone == recipient_phone) | (User.phone == norm_phone))
                except User.DoesNotExist:
                    return "⚠️ Recipient not found. Please check the phone number or invite them to register.", session, True
                recipient_wallet = Wallet.get(Wallet.user == recipient_user, Wallet.currency == asset)
                if sender_wallet.balance < amount:
                    return f"❌ Insufficient funds. Balance: {sender_wallet.balance:,.4f} {asset}", session, True
                with db.atomic():
                    sender_wallet.balance -= amount
                    sender_wallet.save()
                    recipient_wallet.balance += amount
                    recipient_wallet.save()
                    Transaction.create(user=user, type='TRANSFER', currency=asset, amount=amount, status='completed', tx_hash=recipient_phone)
                    Transaction.create(user=recipient_user, type='RECEIVE', currency=asset, amount=amount, status='completed', tx_hash=user.phone)
                # Trigger referral bonus payout if eligible
                from database import trigger_referral_payout
                trigger_referral_payout(user)
                admin_msg = f"🔁 *Internal Transfer*\nSender: {user.phone}\nRecipient: {recipient_user.phone}\nAsset: {asset}\nAmount: {amount}"
                notifications.send_push(type('Admin', (), {'phone': config.OWNER_PHONE.split(',')[0]}), admin_msg)
                return f"✅ Transfer of {amount} {asset} to {recipient_phone} completed.", session, True
            except Wallet.DoesNotExist:
                return f"❌ Wallet not found for asset {asset} or recipient.", session, True
        else:
            return "❌ Transfer aborted.", session, True
    return "❓ Unknown step. Type `menu`.", session, True