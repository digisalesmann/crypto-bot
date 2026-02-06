from database import SupportTicket, User, db
import random
import string

def create_ticket(user, msg):
    """
    Usage: support [message]
    """
    # Remove the word "support" from the message
    clean_msg = msg.replace('support', '', 1).strip()
    
    if not clean_msg:
        return (
            "⚠️ *Support Usage:*\n"
            "Type `support [Your Issue]`\n\n"
            "Example:\n"
            "`support My deposit hasn't arrived`"
        )
        
    SupportTicket.create(
        user=user,
        category='general',
        message=clean_msg,
        status='open'
    )
    
    return (
        "✅ *Ticket Created*\n"
        "━━━━━━━━━━━━━━━━\n"
        "Our team has received your request.\n"
        "We usually reply within 24 hours.\n\n"
        "Type `tickets` to check status."
    )

def get_my_tickets(user):
    tickets = SupportTicket.select().where(SupportTicket.user == user).order_by(SupportTicket.created_at.desc()).limit(3)
    
    if not tickets:
        return "📂 You have no open tickets."
        
    msg = "📂 *Your Support Tickets*\n━━━━━━━━━━━━━━━━\n"
    for t in tickets:
        status_emoji = "🟢" if t.status == 'open' else "🔴"
        msg += f"{status_emoji} *ID {t.id}*: {t.message[:20]}...\n"
        if t.admin_reply:
            msg += f"   ↪️ *Reply:* {t.admin_reply}\n"
    
    return msg

def security_center(user, msg):
    """
    Handles 'freeze', 'report', '2fa'
    """
    if 'freeze' in msg:
        user.is_frozen = True
        user.save()
        return (
            "❄️ *ACCOUNT FROZEN*\n"
            "━━━━━━━━━━━━━━━━\n"
            "✅ All withdrawals disabled.\n"
            "✅ All trading disabled.\n\n"
            "Your funds are safe. Please contact Admin via `support` to unfreeze."
        )
        
    elif '2fa' in msg:
        # Simulate a reset link
        magic_link = "https://cex-bot.com/reset-2fa/" + ''.join(random.choices(string.ascii_letters, k=10))
        return (
            "🔐 *2FA Reset Request*\n"
            "━━━━━━━━━━━━━━━━\n"
            "Click the secure link below to reset your Two-Factor Authentication:\n\n"
            f"{magic_link}\n\n"
            "_(Link expires in 15 minutes)_"
        )
        
    elif 'report' in msg:
        return (
            "🚨 *Report Activity*\n"
            "Please describe the suspicious activity using:\n"
            "`support [REPORT] details...`"
        )

    return (
        "🛡️ *Security Center*\n"
        "━━━━━━━━━━━━━━━━\n"
        "• `freeze` : ❄️ Lock Account instantly\n"
        "• `2fa` : 🔐 Reset 2FA Keys\n"
        "• `report` : 🚨 Report suspicious acts\n\n"
        "💡 *Tip:* Never share your OTP with anyone."
    )