from database import User

def handle_flow(user, msg):
    """
    Manages the multi-step registration process.
    Returns: (Response Text, Is_Finished_Boolean)
    """
    
    # STEP 1: WELCOME & LANGUAGE
    if user.onboarding_status == 'new':
        user.onboarding_status = 'language'
        user.save()
        return (
            "👋 *Welcome to CEX Pro*\n"
            "━━━━━━━━━━━━━━━━\n"
            "The professional interface for seamless crypto trading.\n\n"
            "🌐 *Select Language / Idioma:*\n"
            "• Type *1* for English 🇬🇧\n"
            "• Type *2* for Español 🇪🇸\n"
            "• Type *3* for Français 🇫🇷", 
            False # Not finished yet
        )

    # STEP 2: HANDLE LANGUAGE INPUT
    if user.onboarding_status == 'language':
        if msg == '1' or 'english' in msg:
            user.language = 'en'
        elif msg == '2' or 'espanol' in msg:
            user.language = 'es'
        elif msg == '3' or 'francais' in msg:
            user.language = 'fr'
        else:
            return ("⚠️ Please type *1*, *2*, or *3* to select language.", False)
        
        # Save and move to next step
        user.onboarding_status = 'referral'
        user.save()
        
        return (
            "✅ *Language Set!*\n\n"
            "🎟️ *Referral Code*\n"
            "━━━━━━━━━━━━━━━━\n"
            "Do you have a code from a friend?\n\n"
            "• Type the *Code* to claim bonus\n"
            "• Type *Skip* to continue",
            False
        )

    # STEP 3: HANDLE REFERRAL INPUT
    if user.onboarding_status == 'referral':
        if msg != 'skip':
            user.referral_code = msg.upper()
        
        # COMPLETE ONBOARDING
        user.onboarding_status = 'active'
        user.save()
        
        return (
            "🎉 *Setup Complete!*\n"
            "Your account is now active.\n\n"
            "Type *menu* to access the terminal.",
            True # Finished!
        )

    return (None, True)