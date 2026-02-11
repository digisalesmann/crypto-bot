import config
import uuid
from database import Transaction, db
from modules import notifications
from static_deposit_addresses import STATIC_DEPOSIT_ADDRESSES

def handle_flow(user, msg, session):
    # Block if account is frozen
    if getattr(user, 'is_frozen', False):
        return ("❄️ Your account is currently frozen. Deposits are disabled. Contact support to unfreeze.", session, True)
    step = session.get('step')
    msg_clean = msg.strip().lower()
    
    # --- GLOBAL EXIT ---
    if msg_clean in ['cancel', 'exit', 'stop', 'abort']:
        return "❌ Deposit process cancelled. Type `menu` to restart.", session, True

    # --- STEP 1: Method Selection ---
    if step == 1:
        session['step'] = 2
        return (
            "🏦 *PPAY Deposit Center*\n"
            "━━━━━━━━━━━━━━━━\n"
            "How would you like to fund your account?\n\n"
            "1. Crypto (USDT, BTC, etc.)\n"
            "2. Fiat (Bank Transfer)\n"
            "3. P2P (CashApp, PayPal, Zelle, etc.)\n\n"
            "Reply with a number (1-3) or the name."
        ), session, False

    # --- STEP 2: Handle Initial Method Selection ---
    if step == 2:
        if msg_clean in ['1', 'crypto']:
            session['mode'] = 'crypto'
            session['step'] = 3
            return "*Select Asset:*\n1. USDT\n2. BTC\n3. ETH\n4. SOL", session, False
        
        elif msg_clean in ['2', 'fiat', 'bank']:
            session['mode'] = 'fiat_bank'
            session['step'] = 4
            return "Enter amount in *NGN* you wish to deposit:", session, False
            
        elif msg_clean in ['3', 'p2p', 'cashapp', 'paypal', 'zelle']:
            session['step'] = 2.5
            return (
                "*Select P2P Method:*\n"
                "1. CashApp\n2. PayPal\n3. Zelle\n4. Venmo\n5. Cashmail"
            ), session, False
        
        else:
            return "❓ Invalid choice. Please select 1, 2, or 3.", session, False

    # --- STEP 2.5: P2P Method Selection ---
    if step == 2.5:
        p2p_map = {'1': 'fiat_cashapp', '2': 'fiat_paypal', '3': 'fiat_zelle', '4': 'fiat_venmo', '5': 'fiat_cashmail'}
        selected = p2p_map.get(msg_clean, f"fiat_{msg_clean}")
        session['mode'] = selected
        session['step'] = 4
        return f"Enter amount in *USD* you wish to deposit via {selected.split('_')[1].title()}:", session, False


    # --- STEP 3: Crypto Asset & Network Logic ---
    if step == 3:
        asset_map = {'1': 'USDT', '2': 'BTC', '3': 'ETH', '4': 'SOL'}
        asset = asset_map.get(msg_clean, msg.upper().strip())
        session['coin'] = asset

        # Define networks for specific assets
        if asset == 'USDT':
            session['step'] = 3.5
            return (
                "*Select USDT Network:*\n"
                "1. TRC20 (Tron)\n"
                "2. ERC20 (Ethereum)\n"
                "3. BEP20 (BSC)\n"
                "4. SOL (Solana)"
            ), session, False
        elif asset == 'BTC':
            session['step'] = 3.5
            return "🌐 *Select BTC Network:*\n1. Bitcoin (Native)\n2. BEP20 (BSC)", session, False
        else:
            # ETH/SOL default to native
            session['network'] = asset
            session['step'] = 3.7
            return "Enter amount you wish to deposit (in {}):".format(asset), session, False

    # --- STEP 3.5: Crypto Network Selection ---
    if step == 3.5:
        asset = session.get('coin')
        net_options = {
            'USDT': {'1': 'TRC20', '2': 'ERC20', '3': 'BEP20', '4': 'SOL'},
            'BTC': {'1': 'BTC', '2': 'BEP20'}
        }
        net_map = net_options.get(asset, {})
        session['network'] = net_map.get(msg_clean, msg.upper().strip())
        session['step'] = 3.7
        return "Enter amount you wish to deposit (in {}):".format(asset), session, False

    # --- STEP 3.7: Crypto Amount Entry ---
    if step == 3.7:
        try:
            amt = float(msg_clean.replace(',', ''))
            session['input_val'] = str(amt)
            return show_crypto_address(user, session)
        except ValueError:
            return "❌ Invalid amount. Please enter numbers only.", session, False

    # --- STEP 4: Amount Entry (Fiat/P2P) ---
    if step == 4:
        # Validate that msg is a number
        try:
            amt = float(msg_clean.replace(',', ''))
            session['input_val'] = str(amt)
            return show_fiat_details(session)
        except ValueError:
            return "❌ Invalid amount. Please enter numbers only.", session, False

    # --- STEP 5: Capture Verification (Sender Name) ---
    if step == 5:
        if 'paid' not in msg_clean:
            return "⏳ Please complete the transfer first, then reply with *PAID*.", session, False
        session['step'] = 6
        return "To verify, enter the *Full Name* or *Handle* used to send the funds:", session, False


    # --- STEP 6: Final Log & Notification ---
    if step == 6:
        session['sender_info'] = msg.strip()
        mode = session.get('mode')
        val = session.get('input_val', '0')

        try:
            with db.atomic():
                Transaction.create(
                    user=user,
                    type='DEPOSIT',
                    currency='NGN' if mode == 'fiat_bank' else ('USD' if 'fiat' in mode else session.get('coin')),
                    amount=float(val) if 'fiat' in mode else float(val),
                    status='pending',
                    tx_hash=f"Mode: {mode} | Net: {session.get('network', 'N/A')} | Sender: {session['sender_info']}"
                )

            # Notify Admin
            if mode == 'crypto':
                asset = session.get('coin', 'N/A')
                network = session.get('network', 'N/A')
                addr = STATIC_DEPOSIT_ADDRESSES.get(network, {}).get(asset, 'N/A')
                admin_msg = (
                    f"🚨 *NEW CRYPTO DEPOSIT REQUEST*\n"
                    f"User: {user.phone}\n"
                    f"Asset: {asset}\n"
                    f"Network: {network}\n"
                    f"Address: {addr}\n"
                    f"Amount: {val}\n"
                    f"Sender: {session['sender_info']}"
                )
            else:
                admin_msg = (
                    f"🚨 *NEW DEPOSIT REQUEST*\n"
                    f"User: {user.phone}\n"
                    f"Method: {mode}\n"
                    f"Amount: {val}\n"
                    f"Ref: {session['sender_info']}"
                )
            notifications.notify_admins(admin_msg)

            return (
                "✅ *Submission Successful!*\n"
                "━━━━━━━━━━━━━━━━\n"
                "Our agents are verifying your payment. Your wallet will be credited "
                "automatically once confirmed. Thank you for choosing PPAY!"
            ), session, True
        except Exception as e:
            return f"❌ System Error logging deposit: {e}", session, True

    return "❓ Unknown input. Type `cancel`.", session, True

# --- HELPER FUNCTIONS ---

def show_crypto_address(user, session):
    coin = session.get('coin')
    net = session.get('network')
    addr = STATIC_DEPOSIT_ADDRESSES.get(net, {}).get(coin)
    
    if not addr:
        return f"⚠️ No address found for {coin} on {net}. Contact @Admin.", session, True

    session['step'] = 5 # Move to the "PAID" step
    return (
        f"🏦 *Deposit {coin}*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🌐 Network: *{net}*\n"
        f"📍 Address: `{addr}`\n\n"
        "⚠️ *CRITICAL:*\n"
        f"Send only {coin} via the *{net}* network. Wrong network = lost funds.\n\n"
        "Reply 'PAID' once you have sent the transaction."
    ), session, False

def show_fiat_details(session):
    mode = session.get('mode')
    amt = session.get('input_val')
    session['step'] = 5
    
    instr = {
        'fiat_bank': f"Bank: Kuda Bank\nAcct: 3003394877\nName: Prosper Digital Systems Ltd\nAmt: ₦{float(amt):,.2f}",
        'fiat_cashapp': f"CashApp Handle: $ProsperDigital\nAmt: ${float(amt):,.2f}",
        'fiat_paypal': f"PayPal (F&F): paypal@prosperdigital.com\nAmt: ${float(amt):,.2f}",
        'fiat_zelle': f"Zelle: zelle@prosperdigital.com\nAmt: ${float(amt):,.2f}",
        'fiat_venmo': f"Venmo: @ProsperDigital\nAmt: ${float(amt):,.2f}"
    }
    
    details = instr.get(mode, f"Contact Admin for {mode} details.\nAmt: {amt}")
    return (
        f"💳 *PAYMENT INSTRUCTIONS*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{details}\n\n"
        "⚠️ *Action Required:*\n"
        "Make the transfer now, then reply *PAID* to provide your verification name."
    ), session, False