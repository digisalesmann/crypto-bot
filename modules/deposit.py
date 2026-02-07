# modules/deposit.py
from static_deposit_addresses import STATIC_DEPOSIT_ADDRESSES

def handle_flow(user, msg, session):
    step = session.get('step')
    
    # Step 1: Method Selection
    if step == 1:
        session['step'] = 2
        return "🏦 *Deposit to PPAY*\nChoose Method:\n1. Crypto (USDT, BTC, etc.)\n2. Fiat (Bank Transfer)", session, False
    
    # Step 2: Asset Choice
    if step == 2:
        msg_clean = msg.strip().lower()
        if msg_clean in ['1', 'crypto']:
            session['mode'] = 'crypto'
            session['step'] = 3
            return "Select Coin: `USDT`, `BTC`, `ETH`, `SOL`", session, False
        elif msg_clean in ['2', 'fiat']:
            session['mode'] = 'fiat'
            session['step'] = 4
            return "Enter Amount (NGN) you want to deposit:", session, False
        else:
            return "Please reply with '1' or 'crypto' for Crypto, or '2' or 'fiat' for Fiat Deposit.", session, False

    # Step 3: Crypto Address Generation
    if step == 3:
        session['coin'] = msg.upper().strip()
        session['step'] = 10  # Move to confirmation step
        # Try to find the address in STATIC_DEPOSIT_ADDRESSES
        addr = None
        for chain in STATIC_DEPOSIT_ADDRESSES.values():
            if session['coin'] in chain:
                addr = chain[session['coin']]
                break
        if not addr:
            addr = "Contact Admin for Address"
        return (
            f"🏦 *Deposit {session['coin']} ({session['coin']})*\n"
            f"━━━━━━━━━━━━━━\n"
            f"Send only {session['coin']} via {session['coin']} to:\n\n"
            f"`{addr}`\n\n"
            f"⚠️ *IMPORTANT:*\n"
            f"Include your User ID (*{getattr(user, 'id', 'N/A')}*) in the memo or send a screenshot to Support.\n"
            f"Funds will be credited after 1 confirmation.",
            session,
            False
        )
    
    # Step 4: Fiat Instructions
    if step == 4:
        session['amt'] = msg.strip()
        session['step'] = 11 # Move to payment confirmation step
        return (
            f"💳 *Transfer {session['amt']} NGN to:*\n"
            "Bank: GTBank\n"
            "Acct: 0123456789\n"
            "Name: PPAY GLOBAL\n\n"
            "Once you have made the transfer, type *'PAID'*."
        ), session, False

    # Step 11: Ask for sender name after user types 'PAID'
    if step == 11:
        if msg.strip().lower() == 'paid':
            session['step'] = 12
            return ("Please enter the sender's account name for verification:", session, False)
        # If not 'paid', repeat instruction
        return ("Once you have made the transfer, type *'PAID'*.", session, False)

    # Step 12: Final confirmation after sender name
    if step == 12:
        session['sender_name'] = msg.strip()
        session['step'] = 99 # End or next step
        # Notify Admin
        from modules import notifications
        import config
        admin_msg = f"💳 *Fiat Deposit Request*\nUser: {user.phone}\nAmount: {session['amt']} NGN\nSender: {session['sender_name']}"
        notifications.send_push(type('Admin', (), {'phone': config.OWNER_PHONE.split(',')[0]}), admin_msg)
        return (
            f"✅ *Request Logged!*\nOur team is verifying your payment from account name: *{session['sender_name']}*. Your wallet will be credited automatically upon confirmation.",
            session,
            True
        )

    # Final Confirmation Steps (Closes the session)
    if step in [10, 11]:
        if msg.lower() in ['done', 'paid']:
            # Here you would typically trigger an admin notification
            return "✅ *Request Logged!*\nOur team is verifying your payment. Your wallet will be credited automatically upon confirmation.", session, True

    return "❓ Unknown input. Type `cancel` to exit or follow the instructions above.", session, False