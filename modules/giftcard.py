import os
import datetime
import csv
import config
from modules import notifications

def handle_flow(user, msg, session):
    # Block if account is frozen
    if getattr(user, 'is_frozen', False):
        return ("❄️ Your account is currently frozen. Giftcard redemption is disabled. Contact support to unfreeze.", session, True)

    step = session.get('step', 1)
    cancel_words = ['cancel', 'exit', 'stop', 'abort']

    if msg.lower() in cancel_words:
        return "❌ Redemption cancelled. Type `menu` to restart.", session, True

    # STEP 1: Card Type
    if step == 1:
        session['step'] = 2
        return (
            "🎁 *Gift Card Redemption*\n"
            "━━━━━━━━━━━━━━━━\n"
            "What type of card are you redeeming?\n"
            "(e.g., Amazon, Steam, iTunes, Sephora)",
            session, False
        )

    # STEP 2: Country / Region
    elif step == 2:
        session['card_type'] = msg.strip().upper()
        session['step'] = 3
        return f"🌍 What is the *Country/Currency* for this {session['card_type']} card?\n(e.g., USA, UK, EUR)", session, False

    # STEP 3: Card Mode (Physical vs E-code)
    elif step == 3:
        session['country'] = msg.strip().upper()
        session['step'] = 4
        return (
            "📑 *Select Card Mode:*\n"
            "1. Physical Card (Picture)\n"
            "2. E-code (Text only)",
            session, False
        )

    # STEP 4: Amount/Denomination
    elif step == 4:
        mode_map = {'1': 'PHYSICAL', '2': 'ECODE'}
        session['mode'] = mode_map.get(msg.strip(), msg.strip().upper())
        session['step'] = 5
        return f"Enter the *Face Value* (Amount) of the card:", session, False

    # STEP 5: Card Code & Image Prompt
    elif step == 5:
        session['amount'] = msg.strip()
        session['step'] = 6
        return (
            "🔑 *Almost done!*\n"
            "Please type the *Card Code* below.", session, False)

    # STEP 6: Image Upload Step (for physical cards)
    elif step == 6:
        session['code'] = msg.strip()
        # If mode is PHYSICAL, prompt for image upload
        if session.get('mode', '').upper() == 'PHYSICAL':
            session['step'] = 61
            return "📸 Please upload a clear photo of the physical card (or type 'skip' if you don't have one).", session, False
        else:
            session['step'] = 7
            return giftcard_review_summary(session), session, False

    # STEP 61: Handle image or skip
    elif step == 61:
        if msg.lower() == 'skip' and not session.get('media_url'):
            session['image'] = None
        else:
            session['image'] = session.get('media_url') or msg
        session['step'] = 7
        return giftcard_review_summary(session), session, False

    # STEP 7: Execution & Admin Logging
    elif step == 7:
        if 'yes' in msg.lower():
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_path = 'logs/giftcard_redemptions.log'

            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)

            # Log format: Phone, Type, Code, Status, Time, Country, Amount, Mode
            with open(log_path, 'a', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter='\t')
                writer.writerow([
                    user.phone, session['card_type'], session['code'],
                    'PENDING', timestamp, session['country'],
                    session['amount'], session['mode']
                ])

            # Create Transaction record for admin tracking
            from database import Transaction, db
            try:
                with db.atomic():
                    Transaction.create(
                        user=user,
                        type='GIFTCARD',
                        currency=session.get('country', 'N/A'),
                        amount=float(session.get('amount', 0)),
                        status='pending',
                        tx_hash=session.get('code', '')
                    )
            except Exception as e:
                notifications.notify_admins(f"Giftcard DB log error: {e}")

            image_info = "\n📸 Image: Attached" if session.get('image') else "\n📸 Image: None"
            region_info = f"Region: {session.get('country', 'N/A')}\n"
            admin_alert = (
                f"🚨 *NEW GIFT CARD ALERT*\n"
                f"User: {user.phone}\n"
                f"Card: {session['card_type']} ({session['amount']})\n"
                f"{region_info}"
                f"Code: {session['code']}"
                f"{image_info}"
            )
            notifications.notify_admins(admin_alert)
            return (
                "✅ *Submission Successful!*\n"
                "Your card is now being verified by our agents. "
                "You will be notified and your wallet credited once confirmed."
            ), session, True
        else:
            return "❌ Submission aborted.", session, True

    return "❓ Unknown step. Type `menu`.", session, True

# Helper: Review summary

def giftcard_review_summary(session):
    summary = (
        "⏳ *REVIEW SUBMISSION*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"Type: {session.get('card_type', '')}\n"
        f"Region: {session.get('country', '')}\n"
        f"Mode: {session.get('mode', '')}\n"
        f"Value: {session.get('amount', '')}\n"
        f"Code: `{session.get('code', '')}`\n"
        f"Image: {'Attached' if session.get('image') else 'None'}\n\n"
        "Is this correct? Type *YES* to submit or *CANCEL*."
    )
    return summary