def get_main_menu(user_name=None):
    """
    Personalized entry point for the bot.
    """
    header = f"👋 *Welcome to PPAY, {user_name}!*\n" if user_name else "👋 *Welcome to PPAY!*\n"
    header += "Your premium OTC, Crypto & VTU desk.\n\n"
    return header + get_help_text()

def get_help_text():
    """
    The full command list for standard users.
    """
    return (
        "📚 *COMMAND DASHBOARD*\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "🟢 *GETTING STARTED*\n"
        "• `menu` / `start` : Main dashboard\n"
        "• `balance` : View crypto & fiat funds\n"
        "• `history` : View last 5 transactions\n"
        "\n"
        "💸 *DEPOSIT & WITHDRAW*\n"
        "• `deposit` : Multi-step deposit flow\n"
        "• `deposit [COIN] [CHAIN]` : Direct address\n"
        "• `withdraw` : Multi-step withdrawal flow\n"
        "\n"
        "💱 *FIAT DASHBOARD*\n"
        "• `otc`, `p2p`, `fiat` : View NGN/USDT rates and fiat dashboard\n"
        "\n"
        "🔄 *SWAP & CONVERT*\n"
        "• `swap` : Convert assets (e.g., USDT to NGN)\n"
        "\n"
        "🔁 *INTERNAL TRANSFER*\n"
        "• `transfer` : Send funds to another PPAY user\n"
        "\n"
        "📱 *VTU*\n"
        "• `vtu` : Buy Airtime or Data bundles\n"
        "\n"
        "🎁 *GIFTCARD REDEEM*\n"
        "• `redeem` : Sell giftcards for instant credit\n"
        "\n"
        "📝 *SUPPORT & SECURITY*\n"
        "• `support` : Open a ticket or contact admin\n"
        "• `security` : Freeze account or check 2FA\n"
        "\n"
        "🔔 *MARKET DATA*\n"
        "• `price [COIN]` : Live market rates\n"
        "• `alert [COIN] [PRICE]` : Set price alarm\n"
        "\n"
        "💡 *TIP:* Type `cancel` at any time to stop a process."
    )

def get_admin_help():
    """
    The command list reserved for admins only.
    """
    return (
        "🕵️ *ADMIN CONTROL PANEL*\n"
        "━━━━━━━━━━━━━━━━\n"
        "• `users` : List all registered users\n"
        "• `withdrawals` : View pending requests\n"
        "• `pending_giftcards` : Review card submissions\n"
        "• `tickets` : View open support tickets\n"
        "• `approve [ID] [HASH]` : Complete a withdrawal\n"
        "• `credit [PHONE] [AMT] [COIN]` : Manual credit\n"
        "• `broadcast [MSG]` : Message all users"
    )