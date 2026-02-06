"""
Swap module for handling asset swaps (crypto/fiat).
"""

def start_swap_session(user):
    """Initialize a swap session for the user."""
    return {
        'step': 0,
        'from_asset': None,
        'to_asset': None,
        'amount': None,
        'rate': None,
        'estimate': None
    }


def handle_swap_flow(user, msg, session, price_lookup):
    """
    Conversational swap flow handler.
    - user: user object
    - msg: incoming message (str)
    - session: dict (swap session state)
    - price_lookup: function(from_asset, to_asset) -> rate
    Returns: (response_text, updated_session, done)
    """
    if session['step'] == 0:
        session['step'] = 1
        return ("Which asset do you want to swap from? (e.g. USDT, BTC, ETH)", session, False)
    elif session['step'] == 1:
        session['from_asset'] = msg.strip().upper()
        session['step'] = 2
        return ("Which asset do you want to swap to?", session, False)
    elif session['step'] == 2:
        session['to_asset'] = msg.strip().upper()
        session['step'] = 3
        return (f"How much {session['from_asset']} do you want to swap?", session, False)
    elif session['step'] == 3:
        try:
            amount = float(msg.replace(',', ''))
            if amount <= 0:
                return ("Amount must be greater than zero.", session, False)
            session['amount'] = amount
            # Get rate
            rate = price_lookup(session['from_asset'], session['to_asset'])
            if not rate:
                return (f"No rate available for {session['from_asset']} to {session['to_asset']}.", session, True)
            session['rate'] = rate
            session['estimate'] = round(amount * rate, 8)
            session['step'] = 4
            summary = (
                f"Swap {amount} {session['from_asset']} to {session['to_asset']}\n"
                f"Rate: 1 {session['from_asset']} = {rate} {session['to_asset']}\n"
                f"You will receive ≈ {session['estimate']} {session['to_asset']}\n"
                "Type 'yes' to confirm or 'no' to cancel."
            )
            return (summary, session, False)
        except ValueError:
            return ("Invalid amount. Please enter a number.", session, False)
    elif session['step'] == 4:
        if msg.strip().lower() in ['yes', 'y']:
            # Here, you would process the swap (update balances, etc.)
            session['step'] = 5
            return (f"✅ Swap complete! {session['amount']} {session['from_asset']} swapped to {session['estimate']} {session['to_asset']}.", session, True)
        elif msg.strip().lower() in ['no', 'n', 'cancel']:
            return ("Swap cancelled.", session, True)
        else:
            return ("Please type 'yes' to confirm or 'no' to cancel.", session, False)
    else:
        return ("Unknown step. Type 'swap' to start again.", session, True)
