def send_ticket_reply(user, reply_msg):
    """Sends a support ticket reply to the user via WhatsApp."""
    sender = get_sender()
    if not sender:
        print("❌ Twilio Phone not configured in .env")
        return False
    try:
        client.messages.create(
            from_=sender,
            body=f"📝 *Support Reply*\n━━━━━━━━━━━━━━━━\n{reply_msg}",
            to=f"whatsapp:{user.phone}"
        )
        return True
    except Exception as e:
        print(f"❌ Failed to send ticket reply to {user.phone}: {e}")
        return False
import os
import time
import threading
import random
from twilio.rest import Client
from database import User

# Load Config
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone = os.getenv("TWILIO_PHONE")
client = Client(account_sid, auth_token)

def get_sender():
    """Ensures the sender number has the 'whatsapp:' prefix"""
    if not twilio_phone:
        return None
    if twilio_phone.startswith('whatsapp:'):
        return twilio_phone
    return f"whatsapp:{twilio_phone}"

def send_push(user, message_body, media_url=None):
    """
    Sends a proactive message to a specific user. Supports optional media (image).
    """
    sender = get_sender()
    if not sender:
        print("❌ Twilio Phone not configured in .env")
        return False
    try:
        msg_kwargs = {
            'from_': sender,
            'body': message_body,
            'to': f"whatsapp:{user.phone}"
        }
        if media_url:
            # Twilio expects a list of URLs
            msg_kwargs['media_url'] = [media_url] if isinstance(media_url, str) else media_url
        client.messages.create(**msg_kwargs)
        return True
    except Exception as e:
        print(f"❌ Failed to push to {user.phone}: {e}")
        return False

# --- ASYNC BROADCAST LOGIC ---

def broadcast_worker(message_body, admin_phone):
    """
    Background worker that iterates through users and sends announcements.
    """
    users = User.select()
    total = len(users)
    count = 0
    sender = get_sender()
    
    print(f"📢 Starting Broadcast to {total} users...")
    
    for user in users:
        try:
            client.messages.create(
                from_=sender,
                body="📢 *PPAY ANNOUNCEMENT*\n━━━━━━━━━━━━━━━━\n\n" + message_body,
                to=f"whatsapp:{user.phone}"
            )
            count += 1
            # Rate limit to 2 messages per second to keep Twilio happy
            time.sleep(0.5) 
        except Exception as e:
            print(f"⚠️ Skip {user.phone}: {e}")
            continue
            
    # Final report to Admin
    report = f"✅ *Broadcast Complete*\nSent to {count}/{total} active users."
    send_single_direct(admin_phone, report)

def broadcast_all(message_body, admin_phone):
    """
    Triggers the background thread so the admin doesn't wait.
    """
    thread = threading.Thread(target=broadcast_worker, args=(message_body, admin_phone))
    thread.daemon = True
    thread.start()
    return f"🚀 *Broadcast Started*\nSending to all users in the background. I will alert you when finished."

def send_single_direct(phone, text):
    """Helper for sending messages to a raw phone number (like admin reports)"""
    try:
        client.messages.create(from_=get_sender(), body=text, to=f"whatsapp:{phone}")
    except: pass

def notify_admins(message_body):
    """Sends a notification to ALL admin phones configured in OWNER_PHONE."""
    import config
    admin_phones = [p.strip() for p in config.OWNER_PHONE.split(',') if p.strip()]
    for phone in admin_phones:
        send_single_direct(phone, message_body)

# --- TRANSACTIONAL NOTIFICATIONS ---

def send_deposit_confirmation(user, amount, currency):
    msg = (
        "💰 *Deposit Confirmed*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"Your account has been credited with:\n"
        f"✅ *{amount:,.2f} {currency}*\n\n"
        "Type balance to view your updated funds."
    )
    send_push(user, msg)

def send_withdrawal_processed(user, amount, currency, tx_hash):
    msg = (
        "✅ *Withdrawal Successful*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"Sent: *{amount:,.2f} {currency}*\n"
        f"Ref/Hash: {tx_hash}\n\n"
        "The funds are on their way. Thank you for using PPAY!"
    )
    send_push(user, msg)

def send_internal_transfer_notification(user, amount, coin, direction, other_party):
    """
    Notifies user of an internal transfer (sent or received).
    """
    if direction == 'sent':
        msg = (
            f"💸 *Transfer Sent*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"You successfully sent {amount} {coin} to {other_party}\n\n"
            "Transaction processed instantly."
        )
    else:
        msg = (
            f"💸 *Transfer Received*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"You received {amount} {coin} from {other_party}\n\n"
            "Funds are now available in your PPAY wallet."
        )
    send_push(user, msg)