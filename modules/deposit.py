"""
Deposit session handler for step-by-step deposit flow (crypto and fiat).
"""

def start_deposit_session(user):
    return {
        'step': 0,
        'type': None,  # 'crypto' or 'fiat'
        'coin': None,
        'chain': None,
        'method': None,
        'amount': None,
        'sender': None,
        'proof': None
    }

def handle_flow(user, msg, session):
    """
    Conversational deposit flow handler.
    Returns: (response_text, updated_session, done)
    """
    if session['step'] == 0:
        session['step'] = 1
        return ("Would you like to deposit crypto or fiat?", session, False)
    elif session['step'] == 1:
        t = msg.strip().lower()
        if t in ['crypto', 'coin']:
            session['type'] = 'crypto'
            session['step'] = 2
            return ("Which coin? (e.g. USDT, BTC, ETH)", session, False)
        elif t in ['fiat', 'cash', 'bank']:
            session['type'] = 'fiat'
            session['step'] = 5
            return ("Which fiat method? (e.g. bank, paypal, cashapp, zelle)", session, False)
        else:
            return ("Please type 'crypto' or 'fiat' to continue.", session, False)
    # Crypto deposit
    elif session['type'] == 'crypto':
        if session['step'] == 2:
            session['coin'] = msg.strip().upper()
            session['step'] = 3
            return ("Which chain/network? (e.g. BEP20, ERC20, TRC20, SOL, BTC, BNB)", session, False)
        elif session['step'] == 3:
            session['chain'] = msg.strip().upper()
            # Look up the deposit address from static_deposit_addresses.py
            try:
                from static_deposit_addresses import STATIC_DEPOSIT_ADDRESSES
                address = STATIC_DEPOSIT_ADDRESSES.get(session['chain'], {}).get(session['coin'])
                if not address:
                    address = '[No address found for this coin/chain]'
            except Exception:
                address = '[Error loading deposit address]'
            session['step'] = 4
            user_id = getattr(user, 'id', 'your User ID')
            msg_out = (
                f"🏦 *Deposit {session['coin']} ({session['chain']})*\n"
                f"━━━━━━━━━━━━━━\n"
                f"Send only {session['coin']} via {session['chain']} to:\n\n"
                f"`{address}`\n\n"
                f"⚠️ *IMPORTANT:*\nInclude your User ID (*{user_id}*) in the memo or send a screenshot to Support.\n"
                f"Funds will be credited after 1 confirmation."
            )
            return (msg_out, session, False)
        elif session['step'] == 4:
            session['proof'] = msg.strip()
            return ("Deposit submitted! Our admin will credit your wallet after confirmation.", session, True)
    # Fiat deposit
    elif session['type'] == 'fiat':
        if session['step'] == 5:
            session['method'] = msg.strip().lower()
            session['step'] = 6
            return ("How much did you send?", session, False)
        elif session['step'] == 6:
            session['amount'] = msg.strip()
            session['step'] = 7
            return ("What is the sender name/account?", session, False)
        elif session['step'] == 7:
            session['sender'] = msg.strip()
            session['step'] = 8
            return ("(Optional) Send payment proof (screenshot) or type 'skip' to continue.", session, False)
        elif session['step'] == 8:
            session['proof'] = msg.strip()
            return ("Deposit submitted! Our admin will confirm and credit your wallet soon.", session, True)
    return ("Unknown step. Type 'deposit' to start again.", session, True)
