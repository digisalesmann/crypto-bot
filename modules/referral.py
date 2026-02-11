from database import User, Transaction, Wallet
import os

def get_referral_dashboard(user):
    """
    Returns user's referral code, count of successful invites, 
    and total earnings from the referral program.
    """
    # 1. Ensure user has a unique referral code
    if not user.referral_code:
        # New format: PPAY + 4 random uppercase letters + 4 digits (e.g., PPAY-ABCD-1234)
        import random, string
        prefix = "PPAY"
        letters = ''.join(random.choices(string.ascii_uppercase, k=4))
        digits = ''.join(random.choices(string.digits, k=4))
        user.referral_code = f"{prefix}-{letters}-{digits}"
        user.save()

    # 2. Count users WHO WERE REFERRED BY this user
    # Note: This assumes your User model has a 'referred_by' ForeignKeyField
    referral_count = User.select().where(User.referred_by == user).count()

    # 3. Calculate total bonus earned
    # Aggregating in the database is much faster than Python sum() for production
    from peewee import fn
    total_bonus = (Transaction
                   .select(fn.SUM(Transaction.amount))
                   .where(Transaction.user == user, 
                          Transaction.type == 'REFERRAL_BONUS')
                   .scalar() or 0.0)

    # 4. Fetch the current Reward Amount from config/env
    reward_amt = float(os.getenv("REFERRAL_REWARD_NGN", 500.00))

    msg = (
        "🎊 *PPAY REFERRAL PROGRAM*\n"
        "━━━━━━━━━━━━━━━━\n"
        "Invite your friends and earn rewards when they complete their first trade!\n\n"
        f"🔗 *Your Code:* {user.referral_code}\n"
        f"👥 *Total Referrals:* {referral_count}\n"
        f"💰 *Total Earned:* ₦{total_bonus:,.2f}\n\n"
        "📈 *Current Promo:*\n"
        f"Earn *₦{reward_amt:,.0f}* for every active user you bring to the platform.\n\n"
        "💡 *Tip:* Copy and paste your code to your WhatsApp Status to start earning!"
    )
    return msg