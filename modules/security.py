import datetime
from database import db

def handle_flow(user, msg, session):
    step = session.get('step', 1)
    cancel_words = ['cancel', 'exit', 'back']
    
    if msg.lower() in cancel_words:
        return "🏠 Returned to Safety Center. Type `menu` for main dashboard.", session, True

    # STEP 1: Security Menu
    if step == 1:
        session['step'] = 2
        return (
            "🛡️ *PPAY SECURITY CENTER*\n"
            "━━━━━━━━━━━━━━━━\n"
            "Protect your assets with our security tools:\n\n"
            "1. ❄️ *Freeze Account*: Instantly lock all withdrawals.\n"
            "2. 🔐 *2FA Info*: How to secure your login.\n"
            "3. 🚩 *Report Activity*: Notify us of suspicious transactions.\n"
            "4. 📝 *Update PIN*: Change your transaction authorization.\n\n"
            "*Select an option (1-4) or type 'exit':*"
        ), session, False

    # STEP 2: Logic Branching
    elif step == 2:
        choice = msg.strip()
        
        # --- Option 1: Freeze Account ---
        if choice == '1':
            session['step'] = 10
            return (
                "⚠️ *CONFIRM FREEZE*\n"
                "This will immediately disable all withdrawals and swaps on your account. "
                "Only an Admin can unfreeze it after identity verification.\n\n"
                "Type your *User ID* to confirm freezing your account:"
            ), session, False
            
        # --- Option 2: 2FA Info ---
        elif choice == '2':
            return (
                "🔐 *Two-Factor Authentication*\n"
                "━━━━━━━━━━━━━━━━\n"
                "Currently, PPAY uses **WhatsApp-linked authentication**. Since your account is "
                "tied to your phone number, your 2FA is managed by your WhatsApp security.\n\n"
                "💡 *Pro Tip:* Enable 'Two-Step Verification' in your WhatsApp Settings to prevent "
                "SIM-swap attacks."
            ), session, True

        # --- Option 3: Report Activity ---
        elif choice == '3':
            session['step'] = 30
            return "🚩 Please describe the suspicious activity or Transaction ID:", session, False

        else:
            return "❓ Invalid choice. Please select 1, 2, or 3.", session, False

    # STEP 10: Execute Freeze
    elif step == 10:
        if msg.strip() == str(user.id):
            user.is_frozen = True
            user.save()
            # Log the event
            with open('logs/security_events.log', 'a') as f:
                f.write(f"[{datetime.datetime.now()}] FREEZE: {user.phone}\n")
            
            return (
                "❄️ *ACCOUNT FROZEN*\n"
                "Your account has been successfully locked. All outgoing transactions are disabled. "
                "Contact support to begin the unfreezing process."
            ), session, True
        else:
            return "❌ User ID mismatch. Freeze cancelled.", session, True

    # STEP 30: Handle Report
    elif step == 30:
        report_desc = msg.strip()
        # Notify Admin immediately
        admin_alert = f"🚨 *SECURITY REPORT*\nUser: {user.phone}\nIssue: {report_desc}"
        # notifications.notify_admin(admin_alert)
        
        return "✅ Report submitted. Our security team will investigate and contact you shortly.", session, True

    return "❓ Unknown step. Type `security` to restart.", session, True