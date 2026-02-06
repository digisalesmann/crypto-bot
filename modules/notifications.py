import os
import time
from twilio.rest import Client
from database import User

# Load Config
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone = os.getenv("TWILIO_PHONE")
client = Client(account_sid, auth_token)

def get_sender():
    """Ensures the sender number has the 'whatsapp:' prefix"""
    if twilio_phone.startswith('whatsapp:'):
        return twilio_phone
    return f"whatsapp:{twilio_phone}"

def send_push(user, message_body):
    """
    Sends a proactive message to a specific user.
    """
    try:
        message = client.messages.create(
            from_=get_sender(), # <--- FIXED HERE
            body=message_body,
            to=f"whatsapp:{user.phone}"
        )
        return True
    except Exception as e:
        print(f"❌ Failed to push to {user.phone}: {e}")
        return False

def broadcast_all(message_body):
    """
    Sends a message to ALL users.
    """
    users = User.select()
    count = 0
    sender = get_sender() # <--- FIXED HERE
    
    print(f"📢 Starting Broadcast to {len(users)} users...")
    
    for user in users:
        try:
            client.messages.create(
                from_=sender,
                body="📢 *ANNOUNCEMENT*\n━━━━━━━━━━━━━━━━\n" + message_body,
                to=f"whatsapp:{user.phone}"
            )
            count += 1
            time.sleep(0.5) 
        except Exception as e:
            print(f"⚠️ Skip {user.phone}: {e}")
            continue
            
    return f"✅ Broadcast sent to {count} users."

def send_deposit_confirmation(user, amount, currency):
    msg = (
        "💰 *Deposit Confirmed*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"Your account has been credited with:\n"
        f"✅ *{amount:,.2f} {currency}*\n\n"
        "Type `balance` to view funds."
    )
    send_push(user, msg)

def send_withdrawal_processed(user, amount, currency, tx_hash):
    msg = (
        "✅ *Withdrawal Successful*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"Sent: *{amount:,.2f} {currency}*\n"
        f"Ref/Hash: `{tx_hash}`\n\n"
        "Thank you for trading with us."
    )
    send_push(user, msg)

def send_internal_transfer_notification(user, amount, coin, direction, other_party):
    """
    Notifies user of an internal transfer (sent or received).
    direction: 'sent' or 'received'
    other_party: phone number of the other user
    """
    if direction == 'sent':
        msg = (
            f"💸 *Transfer Sent*\n"
            f"You sent `{amount} {coin}` to {other_party}.\n"
            "If this was not you, contact support immediately."
        )
    else:
        msg = (
            f"💸 *Transfer Received*\n"
            f"You received `{amount} {coin}` from {other_party}.\n"
            "Funds are now available in your wallet."
        )
    send_push(user, msg)