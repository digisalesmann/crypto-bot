import datetime
import random
import string
import config
from database import db, Transaction # Assuming you store tickets in a similar table or a dedicated Ticket table
from modules import notifications

def generate_ticket_id():
    """Generates a unique reference like #SUP-A1B2"""
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"SUP-{suffix}"

def handle_flow(user, msg, session):
    step = session.get('step', 1)
    cancel_words = ['cancel', 'exit', 'stop', 'abort']
    
    if msg.lower() in cancel_words:
        return "❌ Support request cancelled. Type `menu` to restart.", session, True

    # STEP 1: Category Selection
    if step == 1:
        session['step'] = 2
        return (
            "☎️ *PPAY Support Center*\n"
            "━━━━━━━━━━━━━━━━\n"
            "What can we help you with today?\n\n"
            "1. Deposit Issue\n"
            "2. Withdrawal Issue\n"
            "3. Swap/Trade Issue\n"
            "4. Account/KYC\n"
            "5. Other / General Inquiry\n\n"
            "*Select a number (1-5):*"
        ), session, False

    # STEP 2: Description
    elif step == 2:
        categories = {
            '1': 'DEPOSIT', '2': 'WITHDRAWAL', 
            '3': 'SWAP', '4': 'ACCOUNT', '5': 'OTHER'
        }
        session['category'] = categories.get(msg.strip(), 'GENERAL')
        session['step'] = 3
        return (
            f"📝 *Category: {session['category']}*\n"
            "Please describe your issue in detail.\n\n"
            "💡 *Tip:* Be specific (include amounts, dates, or transaction IDs) so we can help you faster."
        ), session, False

    # STEP 3: Image Proof (Optional)
    elif step == 3:
        session['description'] = msg.strip()
        session['step'] = 4
        return (
            "📸 *Upload Proof (Optional)*\n"
            "If you have a screenshot or receipt, please send it now.\n\n"
            "Otherwise, type *'SKIP'* to submit your ticket."
        ), session, False

    # STEP 4: Review and Submit
    elif step == 4:
        # Check if the message contains an image (handled in main.py)
        # If 'media_url' was injected into the session by main.py
        image_status = "✅ Image Attached" if session.get('media_url') else "❌ No Image"
        
        # If they typed skip, we move on. If they sent an image, main.py already updated session.
        if msg.lower() != 'skip' and not session.get('media_url'):
            session['description'] += f"\n[Additional Info: {msg}]"

        session['ticket_id'] = generate_ticket_id()
        session['step'] = 5
        
        summary = (
            "⚠️ *CONFIRM TICKET*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: {session['ticket_id']}\n"
            f"📂 Category: {session['category']}\n"
            f"📄 Issue: {session['description'][:100]}...\n"
            f"🖼 Proof: {image_status}\n\n"
            "Type *YES* to submit to our agents."
        )
        return summary, session, False

    # STEP 5: Final Submission & Notification
    elif step == 5:
        if 'yes' in msg.lower():
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 1. Log to Admin/Database (Example using a text log for simplicity)
            # In a full production app, you would have a 'Ticket' model in database.py
            log_entry = (
                f"[{timestamp}] TICKET {session['ticket_id']}\n"
                f"User: {user.phone}\nCategory: {session['category']}\n"
                f"Description: {session['description']}\n"
                f"Media: {session.get('media_url', 'None')}\n"
                f"{'-'*30}\n"
            )
            
            with open('logs/support_tickets.log', 'a', encoding='utf-8') as f:
                f.write(log_entry)

            # 2. Notify Admins
            admin_alert = (
                f"📩 *NEW SUPPORT TICKET*\n"
                f"ID: {session['ticket_id']}\n"
                f"User: {user.phone}\n"
                f"Cat: {session['category']}"
            )
            from modules import notifications
            import config
            notifications.send_push(type('Admin', (), {'phone': config.OWNER_PHONE.split(',')[0]}), admin_alert)

            return (
                f"✅ *Ticket Submitted!*\n"
                f"Your Reference ID is *{session['ticket_id']}*.\n\n"
                "An agent will review your request and reply to you directly on WhatsApp within 24 hours."
            ), session, True
        else:
            return "❌ Submission aborted.", session, True

    return "❓ Unknown step. Type `menu`.", session, True