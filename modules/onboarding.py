import config
from database import User, Wallet, db

def handle_flow(user, msg):
    """
    Handles the step-by-step onboarding process.
    Returns: (response_text, is_finished)
    """
    msg_clean = msg.strip()

    # --- Step 0: Initial Welcome & Language Selection ---
    if user.onboarding_status == 'new':
        user.onboarding_status = 'step_language'
        user.save()
        return (
            "🌍 *Welcome to PPAY - Your Premium OTC Desk*\n"
            "━━━━━━━━━━━━━━━━\n"
            "To get started, please select your preferred language:\n\n"
            "1. 🇬🇧 UK English\n"
            "2. 🇺🇸 US English\n"
            "3. 🇳🇬 Nigerian English",
            False
        )

    # --- Step 1: Process Language & Ask for Name ---
    if user.onboarding_status == 'step_language':
        langs = {'1': 'en', '2': 'pidgin', '3': 'fr'}
        user.language = langs.get(msg_clean, 'en')
        user.onboarding_status = 'step_name'
        user.save()
        return "👤 Great! What should we call you? (Enter your full name or nickname):", False

    # --- Step 2: Process Name & Ask for Referral (Optional) ---
    if user.onboarding_status == 'step_name':
        if len(msg_clean) < 2:
            return "⚠️ Please enter a valid name (at least 2 characters):", False
        user.name = msg_clean
        user.onboarding_status = 'step_referral'
        user.save()
        return (
            f"Nice to meet you, *{user.name}*!\n\n"
            "🎁 Do you have a **Referral Code**?\n"
            "If yes, type it now. Otherwise, type *'SKIP'*."
        ), False

    # --- Step 3: Referral code logic & Ask for PIN ---
    if user.onboarding_status == 'step_referral':
        if msg_clean.lower() != 'skip':
            code_provided = msg_clean.upper()
            
            # Use the dedicated database helper for attribution
            from database import apply_referral
            success = apply_referral(user, code_provided)
            
            if success:
                # Notify sponsor and update referral count
                sponsor = User.get_or_none(User.referral_code == code_provided)
                if sponsor:
                    try:
                        from modules import notifications
                        referral_count = User.select().where(User.referred_by == sponsor).count()
                        notifications.send_push(sponsor, f"🎉 Someone just signed up with your code!\n👥 Total referrals: {referral_count}")
                    except Exception:
                        pass
            else:
                return (
                    "❌ Invalid referral code. Please check and try again, or type *'SKIP'* to continue.",
                    False
                )

        user.onboarding_status = 'step_pin'
        user.save()
        return (
            "🔒 *Security Setup*\n"
            "━━━━━━━━━━━━━━━━\n"
            "Please set a *4-digit PIN*. This will be required for withdrawals and sensitive actions.\n\n"
            "Enter a 4-digit PIN:",
            False
        )

    # --- Step 4: PIN setup & Finalization ---
    if user.onboarding_status == 'step_pin':
        if not (msg_clean.isdigit() and len(msg_clean) == 4):
            return "❌ PIN must be exactly 4 digits. Please enter a 4-digit PIN:", False
        
        user.pin = msg_clean # In production, consider hashing this
        user.onboarding_status = 'active'
        
        try:
            with db.atomic():
                user.save()
                # Initialize Default Wallets (NGN and USDT)
                Wallet.get_or_create(user=user, currency='NGN', defaults={'balance': 0.0})
                Wallet.get_or_create(user=user, currency='USDT', defaults={'balance': 0.0})
            
            welcome_msg = (
                f"✅ *Onboarding Complete, {user.name}!*\n"
                "━━━━━━━━━━━━━━━━\n"
                "Your PPAY wallets (NGN & USDT) have been activated. 🚀\n\n"
                "💡 *Quick Start:*\n"
                "• Type `menu` to see all features.\n"
                "• Type `deposit` to add funds.\n"
                "• Type `p2p` to see today's OTC exchange prices.\n\n"
                "We are glad to have you on board!"
            )
            return welcome_msg, True

        except Exception as e:
            print(f"❌ Onboarding Error: {e}")
            return "⚠️ An error occurred during setup. Please type `start` to try again.", False

    return None, False