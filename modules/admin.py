import datetime

def admin_menu():
    return (
        "*ADMIN DASHBOARD*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "*User Management*\n"
        "• users: List all users\n"
        "• credit: Credit user\n"
        "• unfreeze: Unfreeze a user account\n"
        "\n"
        "*Withdrawals & Deposits*\n"
        "• withdrawals: Pending withdrawals\n"
        "• deposits: Pending deposits\n"
        "• approve: Approve withdrawal\n"
        "\n"
        "*Giftcards*\n"
        "• gift: Pending giftcards\n"
        "• approve giftcard: Approve or reject giftcard\n"
        "\n"
        "*Communication*\n"
        "• broadcast: Send broadcast\n"
        "• tickets: Open support tickets\n"
        "• reply: Reply to ticket\n"
        "\n"
        "*Menu/Help*\n"
        "• admin: Show this menu\n"
        "• help: Show this menu\n"
    )

def get_pending_deposits():
    from database import Transaction
    pending = Transaction.select().where(
        (Transaction.type.in_(['FIAT_DEPOSIT', 'CRYPTO_DEPOSIT', 'DEPOSIT'])) & (Transaction.status == 'pending')
    ).order_by(Transaction.timestamp.asc())
    if not pending:
        return "✅ *Deposit Desk:* No pending deposits."
    msg = "*PENDING DEPOSITS*\n━━━━━━━━━━━━━━━━\n"
    for tx in pending:
        # Default values
        asset = tx.currency
        method = 'Unknown'
        # For new unified DEPOSIT type, parse tx_hash for mode
        if tx.type == 'DEPOSIT':
            # Example: Mode: fiat_cashapp | Net: N/A | Sender: John Doe
            mode = 'unknown'
            if tx.tx_hash and 'Mode:' in tx.tx_hash:
                try:
                    mode = tx.tx_hash.split('Mode:')[1].split('|')[0].strip()
                except Exception:
                    mode = 'unknown'
            # Determine method and asset
            if mode == 'crypto':
                method = 'Crypto'
                asset = tx.currency
            elif mode == 'fiat_bank':
                method = 'Fiat (Bank)'
                asset = 'NGN'
            elif mode.startswith('fiat_'):
                method = f"P2P ({mode.split('_',1)[1].title()})"
                asset = 'USD'
            else:
                method = mode.title()
        elif tx.type == 'FIAT_DEPOSIT':
            method = 'Fiat (Bank)'
            asset = tx.currency
        elif tx.type == 'CRYPTO_DEPOSIT':
            method = 'Crypto'
            asset = tx.currency
        msg += f"ID {tx.id} | {tx.user.phone}\n"
        msg += f"Amount: {tx.amount:,.2f} {asset} ({method})\n"
        msg += f"Reference: {tx.tx_hash}\n\n"
    msg += "Approve: approve deposit [ID] [REF]"
    return msg
def get_pending_giftcards():
    """Lists pending giftcard redemptions."""
    pending = Transaction.select().where(
        (Transaction.type == 'GIFTCARD') &
        (Transaction.status == 'pending')
    ).order_by(Transaction.timestamp.asc())
    if not pending:
        return "*Giftcard Desk:* No pending giftcard redemptions."
    msg = "*PENDING GIFTCARDS*\n━━━━━━━━━━━━━━━━\n"
    for tx in pending:
        msg += f"ID {tx.id} | {tx.user.phone}\n"
        msg += f"Amount: {tx.amount:,.2f} {tx.currency}\n"
        msg += f"Reference: {tx.tx_hash}\n\n"
    msg += "Approve: approve giftcard [ID] [REF]"
    return msg
def handle_approve_giftcard_flow(user, msg, session):
    step = session.get('step', 1)
    cancel_words = ['cancel', 'abort', 'exit', 'stop']
    if msg.strip().lower() in cancel_words:
        return ("❌ Giftcard approval process cancelled.", session, True)

    if step == 1:
        session['step'] = 2
        return ("Enter the giftcard transaction ID to approve:", session, False)
    elif step == 2:
        tx_id = msg.strip()
        session['tx_id'] = tx_id
        session['step'] = 3
        return ("Enter the reference or transaction hash for this giftcard (or type None to skip):", session, False)
    elif step == 3:
        ref = msg.strip()
        if ref.lower() == 'none':
            ref = ''
        session['ref'] = ref
        # Confirm details
        tx_id = session['tx_id']
        confirm_msg = (
            f"Confirm giftcard approval:\nGiftcard ID: {tx_id}\nReference: {ref if ref else 'N/A'}\n\nReply YES to approve, REJECT to decline, or CANCEL to abort."
        )
        session['step'] = 4
        return (confirm_msg, session, False)
    elif step == 4:
        msg_clean = msg.strip().lower()
        if msg_clean == 'yes':
            tx_id = session['tx_id']
            ref = session['ref']
            admin_phone = config.OWNER_PHONE.split(',')[0]
            tx = Transaction.get_or_none((Transaction.id == tx_id) & (Transaction.type == 'GIFTCARD'))
            if not tx:
                return (f"❌ Error: Giftcard transaction ID not found. Type CANCEL to abort or enter a different ID:", session, False)
            if tx.status == 'completed':
                return ("⚠️ Notice: This giftcard was already approved.", session, True)
            with db.atomic():
                tx.status = 'completed'
                tx.tx_hash = ref
                tx.save()
            log_admin_action(admin_phone, f"Approved giftcard ID {tx_id} with Ref {ref if ref else 'N/A'}")
            # Notify user of approval (production-grade)
            try:
                from modules import notifications
                approved_msg = (
                    "🎉 *Gift Card Approved!*\n"
                    "━━━━━━━━━━━━━━━━\n"
                    f"Your gift card redemption (ID: {tx_id}) has been approved and is being processed.\n"
                    f"Reference: {ref if ref else 'N/A'}\n\n"
                    "You will be credited shortly. Thank you for using PPAY!"
                )
                notifications.send_push(tx.user, approved_msg)
            except Exception as notify_err:
                log_admin_action(admin_phone, f"Giftcard approval notification failed for user {tx.user.phone}: {notify_err}")
            return (f"✅ Giftcard {tx_id} successfully approved.", session, True)
        elif msg_clean == 'reject':
            session['step'] = 5
            return ("Please enter a reason for rejecting this giftcard:", session, False)
        else:
            return ("❌ Giftcard approval process cancelled.", session, True)

    elif step == 5:
        # Handle rejection reason
        tx_id = session.get('tx_id')
        reason = msg.strip()
        admin_phone = config.OWNER_PHONE.split(',')[0]
        tx = Transaction.get_or_none((Transaction.id == tx_id) & (Transaction.type == 'GIFTCARD'))
        if not tx:
            return (f"❌ Error: Giftcard transaction ID not found. Type CANCEL to abort or enter a different ID:", session, False)
        if tx.status == 'completed':
            return ("⚠️ Notice: This giftcard was already approved.", session, True)
        with db.atomic():
            tx.status = 'rejected'
            tx.save()
        log_admin_action(admin_phone, f"Rejected giftcard ID {tx_id} | Reason: {reason}")
        # Notify user of rejection (production-grade)
        try:
            from modules import notifications
            reject_msg = (
                "❌ *Gift Card Rejected*\n"
                "━━━━━━━━━━━━━━━━\n"
                f"Your gift card redemption (ID: {tx_id}) was not approved.\n"
                f"Reason: {reason}\n\n"
                "If you have questions, reply SUPPORT to contact us."
            )
            notifications.send_push(tx.user, reject_msg)
        except Exception as notify_err:
            log_admin_action(admin_phone, f"Giftcard rejection notification failed for user {tx.user.phone}: {notify_err}")
        return (f"❌ Giftcard {tx_id} rejected and user notified.", session, True)
    else:
        return ("❓ Unknown step. Type CANCEL to abort.", session, False)
def handle_broadcast_flow(user, msg, session):
    step = session.get('step', 1)
    cancel_words = ['cancel', 'abort', 'exit', 'stop']
    if msg.strip().lower() in cancel_words:
        return ("❌ Broadcast process cancelled.", session, True)

    if step == 1:
        session['step'] = 2
        return ("📢 Enter the message to broadcast to all users:", session, False)
    elif step == 2:
        announcement = msg.strip()
        session['announcement'] = announcement
        # Confirm details
        confirm_msg = (
            f"Confirm broadcast message:\n{announcement}\n\nReply YES to confirm or CANCEL to abort."
        )
        session['step'] = 3
        return (confirm_msg, session, False)
    elif step == 3:
        if msg.strip().lower() == 'yes':
            announcement = session['announcement']
            admin_phone = config.OWNER_PHONE.split(',')[0]
            if len(announcement) < 10:
                return ("❌ Broadcast rejected: Message is too vague. Enter a longer message:", session, False)
            log_admin_action(admin_phone, f"Global Broadcast: {announcement[:20]}...")
            result = notifications.broadcast_all(announcement, admin_phone)
            return (result, session, True)
        else:
            return ("❌ Broadcast process cancelled.", session, True)
    else:
        return ("❓ Unknown step. Type CANCEL to abort.", session, False)
def handle_reply_flow(user, msg, session):
    step = session.get('step', 1)
    cancel_words = ['cancel', 'abort', 'exit', 'stop']
    if msg.strip().lower() in cancel_words:
        return ("❌ Reply process cancelled.", session, True)

    if step == 1:
        session['step'] = 2
        return ("Enter the support ticket ID to reply to:", session, False)
    elif step == 2:
        ticket_id = msg.strip()
        session['ticket_id'] = ticket_id
        session['step'] = 3
        return ("💬 Enter your reply message:", session, False)
    elif step == 3:
        reply_msg = msg.strip()
        session['reply_msg'] = reply_msg
        # Confirm details
        ticket_id = session['ticket_id']
        confirm_msg = (
            f"Confirm reply to ticket:\nTicket ID: {ticket_id}\nReply: {reply_msg}\n\nReply YES to confirm or CANCEL to abort."
        )
        session['step'] = 4
        return (confirm_msg, session, False)
    elif step == 4:
        if msg.strip().lower() == 'yes':
            ticket_id = session['ticket_id']
            reply_msg = session['reply_msg']
            admin_phone = config.OWNER_PHONE.split(',')[0]
            ticket = SupportTicket.get_or_none(SupportTicket.id == ticket_id)
            if not ticket:
                return (f"❌ Ticket ID {ticket_id} not found. Type CANCEL to abort or enter a different ID:", session, False)
            if ticket.status == 'replied':
                return ("⚠️ Notice: This ticket was already replied.", session, True)
            ticket.admin_reply = reply_msg
            ticket.status = 'replied'
            ticket.save()
            log_admin_action(admin_phone, f"Replied to ticket {ticket_id}: {reply_msg[:30]}")
            notifications.send_ticket_reply(ticket.user, reply_msg)
            return (f"✅ Ticket {ticket_id} replied.", session, True)
        else:
            return ("❌ Reply process cancelled.", session, True)
    else:
        return ("❓ Unknown step. Type CANCEL to abort.", session, False)
def handle_approve_flow(user, msg, session):
    step = session.get('step', 1)
    cancel_words = ['cancel', 'abort', 'exit', 'stop']
    if msg.strip().lower() in cancel_words:
        return ("❌ Approve process cancelled.", session, True)

    if step == 1:
        session['step'] = 2
        return ("What are you approving?\nReply with 'deposit' or 'withdrawal'", session, False)
    elif step == 2:
        choice = msg.strip().lower()
        if choice not in ['deposit', 'withdrawal']:
            return ("❓ Please reply with 'deposit' or 'withdrawal'", session, False)
        session['approve_type'] = choice
        session['step'] = 3
        return (f"Enter the {choice} transaction ID to approve:", session, False)
    elif step == 3:
        tx_id = msg.strip()
        session['tx_id'] = tx_id
        session['step'] = 4
        approve_type = session.get('approve_type', 'withdrawal')
        return (f"Enter the reference or transaction hash for this {approve_type} (or type NONE to skip):", session, False)
    elif step == 4:
        ref = msg.strip()
        if ref.lower() == 'none':
            ref = ''
        session['ref'] = ref
        tx_id = session['tx_id']
        approve_type = session.get('approve_type', 'withdrawal')
        confirm_msg = (
            f"Confirm approval:\n{approve_type.capitalize()} ID: {tx_id}\nReference: {ref if ref else 'N/A'}\n\nReply YES to approve, REJECT to decline, or CANCEL to abort."
        )
        session['step'] = 5
        return (confirm_msg, session, False)
    elif step == 5:
        msg_clean = msg.strip().lower()
        if msg_clean == 'yes':
            tx_id = session['tx_id']
            ref = session['ref']
            approve_type = session.get('approve_type', 'withdrawal')
            admin_phone = config.OWNER_PHONE.split(',')[0]
            tx = Transaction.get_or_none(Transaction.id == tx_id)
            # Accept DEPOSIT, FIAT_DEPOSIT, CRYPTO_DEPOSIT for deposit approval
            if approve_type == 'deposit':
                if not tx or tx.type not in ['DEPOSIT', 'FIAT_DEPOSIT', 'CRYPTO_DEPOSIT']:
                    return (f"❌ Error: Transaction ID not found or not a deposit. Type CANCEL to abort or enter a different ID:", session, False)
            else:
                if not tx or tx.type.upper() != f'{approve_type.upper()}_DEPOSIT':
                    return (f"❌ Error: Transaction ID not found or not a withdrawal. Type CANCEL to abort or enter a different ID:", session, False)
            if tx.status == 'completed':
                return (f"⚠️ Notice: This {approve_type} was already processed.", session, True)
            with db.atomic():
                tx.status = 'completed'
                tx.tx_hash = ref
                tx.save()
            log_admin_action(admin_phone, f"Approved {approve_type} ID {tx_id} with Ref {ref if ref else 'N/A'}")
            if approve_type == 'withdrawal':
                notifications.send_withdrawal_processed(tx.user, tx.amount, tx.currency, ref)
                return (f"✅ Withdrawal {tx_id} successfully approved.", session, True)
            else:
                # For deposit, update wallet balance automatically
                from modules import wallet
                # Find or create wallet
                wallet_obj, _ = Wallet.get_or_create(user=tx.user, currency=tx.currency)
                wallet_obj.balance += tx.amount
                wallet_obj.save()
                notifications.send_deposit_confirmation(tx.user, tx.amount, tx.currency)
                return (f"✅ Deposit {tx_id} successfully approved and user credited. New Balance: {wallet_obj.balance:,.2f} {tx.currency}.", session, True)
        elif msg_clean == 'reject':
            session['step'] = 6
            return ("Please enter a reason for rejecting this deposit:", session, False)
        else:
            return ("❌ Approve process cancelled.", session, True)

    elif step == 6:
        # Handle deposit rejection reason
        tx_id = session.get('tx_id')
        reason = msg.strip()
        admin_phone = config.OWNER_PHONE.split(',')[0]
        tx = Transaction.get_or_none(Transaction.id == tx_id)
        if not tx or tx.type not in ['DEPOSIT', 'FIAT_DEPOSIT', 'CRYPTO_DEPOSIT']:
            return (f"❌ Error: Transaction ID not found or not a deposit. Type CANCEL to abort or enter a different ID:", session, False)
        if tx.status == 'completed':
            return ("⚠️ Notice: This deposit was already approved.", session, True)
        with db.atomic():
            tx.status = 'rejected'
            tx.save()
        log_admin_action(admin_phone, f"Rejected deposit ID {tx_id} | Reason: {reason}")
        # Notify user of rejection
        try:
            reject_msg = (
                "❌ *Deposit Rejected*\n"
                "━━━━━━━━━━━━━━━━\n"
                f"Your deposit (ID: {tx_id}) was not approved.\n"
                f"Reason: {reason}\n\n"
                "If you have questions, reply SUPPORT to contact us."
            )
            notifications.send_push(tx.user, reject_msg)
        except Exception as notify_err:
            log_admin_action(admin_phone, f"Deposit rejection notification failed for user {tx.user.phone}: {notify_err}")
        return (f"❌ Deposit {tx_id} rejected and user notified.", session, True)
    else:
        return ("❓ Unknown step. Type CANCEL to abort.", session, False)
def handle_credit_flow(user, msg, session):
    step = session.get('step', 1)
    cancel_words = ['cancel', 'abort', 'exit', 'stop']
    if msg.strip().lower() in cancel_words:
        return ("❌ Credit process cancelled.", session, True)

    if step == 1:
        session['step'] = 2
        return ("Enter the phone number of the user to credit:", session, False)
    elif step == 2:
        phone = msg.strip()
        session['target_phone'] = phone
        session['step'] = 3
        return (f"Enter the amount to credit to {phone}:", session, False)
    elif step == 3:
        try:
            amount = float(msg.strip())
            if amount <= 0:
                return ("❌ Error: Amount must be positive. Enter a valid amount:", session, False)
            session['amount'] = amount
            session['step'] = 4
            return ("💱 Enter the currency (e.g., NGN, USDT):", session, False)
        except ValueError:
            return ("❌ Error: Amount must be a number. Enter the amount:", session, False)
    elif step == 4:
        currency = msg.strip().upper()
        session['currency'] = currency
        # Confirm details
        phone = session['target_phone']
        amount = session['amount']
        confirm_msg = (
            f"Confirm credit:\nUser: {phone}\nAmount: {amount} {currency}\n\nReply YES to confirm or CANCEL to abort."
        )
        session['step'] = 5
        return (confirm_msg, session, False)
    elif step == 5:
        if msg.strip().lower() == 'yes':
            # Perform credit with phone normalization
            phone = session['target_phone']
            amount = session['amount']
            currency = session['currency']
            admin_phone = config.OWNER_PHONE.split(',')[0]
            def normalize_phone(phone):
                phone = phone.strip()
                if phone.startswith('+234'):
                    return phone
                if phone.startswith('0') and len(phone) == 11:
                    return '+234' + phone[1:]
                return phone
            norm_phone = normalize_phone(phone)
            target_user = User.get_or_none((User.phone == phone) | (User.phone == norm_phone))
            if not target_user:
                return (f"❌ User {phone} not found. Type CANCEL to abort or enter a different phone:", session, False)
            with db.atomic():
                wallet, _ = Wallet.get_or_create(user=target_user, currency=currency)
                wallet.balance += amount
                wallet.save()
                tx = Transaction.create(
                    user=target_user,
                    type='DEPOSIT',
                    currency=currency,
                    amount=amount,
                    status='completed',
                    tx_hash=f'ADMIN_CREDIT_BY_{admin_phone}'
                )
            log_admin_action(admin_phone, f"Credited {amount} {currency} to {phone}")
            notifications.send_deposit_confirmation(target_user, amount, currency)
            return (f"✅ SUCCESS: {target_user.name} credited. New Balance: {wallet.balance:,.2f} {currency}.", session, True)
        else:
            return ("❌ Credit process cancelled.", session, True)
    else:
        return ("❓ Unknown step. Type CANCEL to abort.", session, False)
import logging
from peewee import fn
from database import User, Wallet, Transaction, SupportTicket, db
from modules import notifications
import config

# Setup dedicated admin logging
logger = logging.getLogger('admin_actions')
handler = logging.FileHandler('logs/admin_activity.log')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def log_admin_action(admin_phone, action):
    """Internal audit trail for every admin command."""
    import config
    admin_phones = [p.strip() for p in config.OWNER_PHONE.split(',') if p.strip()]
    timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord('', 0, '', 0, '', '', None))
    for phone in admin_phones:
        logger.info(f"ADMIN: {phone} | ACTION: {action}")
        # Optionally, send WhatsApp/SMS notification here if needed

def get_all_users():
    """Returns a paginated or summarized user base report."""
    users = User.select()
    total_users = users.count()
    
    report = f"👥 *PPAY User Base* ({total_users})\n"
    report += "━━━━━━━━━━━━━━━━\n"
    
    # Show last 10 for brevity in WhatsApp, or list all if small
    for u in users.order_by(User.id.desc()).limit(20):
        status = "❄️" if u.is_frozen else "✅"
        report += f"{status} {u.id} | {u.phone} (Lvl {u.kyc_level})\n"
    
    if total_users > 20:
        report += f"\n_...and {total_users - 20} more users._"
    return report

def credit_user(msg, admin_phone):
    """
    Atomic credit logic with safety checks.
    Usage: credit [PHONE] [AMOUNT] [CURRENCY]
    """
    try:
        parts = msg.split()
        if len(parts) < 4:
            return "⚠️ Usage: credit <PHONE> <AMOUNT> <CURRENCY>"

        target_phone = parts[1]
        amount = float(parts[2])
        currency = parts[3].upper()

        if amount <= 0:
            return "❌ Error: Credit amount must be positive."

        target_user = User.get_or_none(User.phone == target_phone)
        if not target_user:
            return f"❌ User {target_phone} not found."

        with db.atomic():
            wallet, _ = Wallet.get_or_create(user=target_user, currency=currency)
            wallet.balance += amount
            wallet.save()

            tx = Transaction.create(
                user=target_user,
                type='DEPOSIT',
                currency=currency,
                amount=amount,
                status='completed',
                tx_hash=f'ADMIN_CREDIT_BY_{admin_phone}'
            )

        log_admin_action(admin_phone, f"Credited {amount} {currency} to {target_phone}")
        notifications.send_deposit_confirmation(target_user, amount, currency)

        return f"✅ SUCCESS: {target_user.name} credited. New Balance: {wallet.balance:,.2f} {currency}."

    except ValueError:
        return "❌ Error: Amount must be a valid number."
    except Exception as e:
        return f"⚠️ System Error: {str(e)}"

def get_pending_withdrawals():
    """Lists pending withdrawals with a professional, high-density UI."""
    pending = Transaction.select().where(
        (Transaction.type == 'WITHDRAWAL') & 
        (Transaction.status == 'pending')
    ).order_by(Transaction.timestamp.asc())
    
    if not pending:
        return "💎 *ADMIN DASHBOARD*\n━━━━━━━━━━━━━━━━\n✅ All payouts are currently up to date."
        
    msg = "🕵️ *PENDING PAYOUT REQUESTS*\n"
    msg += "━━━━━━━━━━━━━━━━\n\n"
    
    for tx in pending:
        # Time Logic
        wait_time = datetime.datetime.now() - tx.timestamp
        total_seconds = wait_time.total_seconds()
        
        # Format time for better UX (Minutes if < 1h, else Hours)
        if total_seconds < 3600:
            time_display = f"{int(total_seconds // 60)}m ago"
        else:
            time_display = f"{int(total_seconds // 3600)}h ago"

        # Currency Styling
        c_emoji = "🇳🇬" if tx.currency == "NGN" else "🪙"
        
        # Header with Ticket ID and relative time
        msg += f"📦 *TICKET #{tx.id}* — ⏳ {time_display}\n"
        msg += f"━━━━━━━━━━━━━━━━\n"
        msg += f"👤 *USER:* {tx.user.phone}\n"
        msg += f"💰 *AMT:* {c_emoji} {tx.amount:,.2f} {tx.currency}\n"
        msg += f"📍 *DEST:* {tx.tx_hash}\n"
        msg += f"────────────────\n\n" 
        
    msg += "📑 *ACTIONS:*\n"
    msg += "• Reply approve [ID] [REF] to finalize.\n"
    msg += "• Reply reject [ID] [REASON] to cancel."
    
    return msg

def approve_withdrawal(msg, admin_phone):
    """Marks a withdrawal as paid and logs the external reference."""
    try:
        parts = msg.split()
        if len(parts) < 3:
            return "⚠️ Usage: approve [ID] [TX_HASH/REF]"

        tx_id = parts[1]
        ref = " ".join(parts[2:]) 

        tx = Transaction.get_or_none(Transaction.id == tx_id)
        if not tx or tx.type != 'WITHDRAWAL':
            return "❌ Error: Transaction ID not found."
        
        if tx.status == 'completed':
            return "⚠️ Notice: This withdrawal was already processed."

        with db.atomic():
            tx.status = 'completed'
            tx.tx_hash = ref
            tx.save()

        log_admin_action(admin_phone, f"Approved withdrawal ID {tx_id} with Ref {ref}")
        notifications.send_withdrawal_processed(tx.user, tx.amount, tx.currency, ref)
        
        return f"✅ Withdrawal {tx_id} successfully approved."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def send_broadcast(msg, admin_phone):
    """Safety-checked global messaging."""
    announcement = msg.replace('broadcast', '', 1).strip()
    
    if not announcement:
        return "⚠️ Usage: broadcast [Message]"

    # Production safety: Confirm if message is too short
    if len(announcement) < 10:
        return "❌ Broadcast rejected: Message is too vague."

    log_admin_action(admin_phone, f"Global Broadcast: {announcement[:20]}...")
    
    # Notifications module should handle async/threaded delivery 
    # to avoid blocking the bot for large user bases
    return notifications.broadcast_all(announcement)

def get_open_tickets():
    """Lists support tickets categorized by urgency."""
    tickets = SupportTicket.select().where(SupportTicket.status == 'open').order_by(SupportTicket.created_at.asc())
    if not tickets: return "✅ *Support Desk:* All tickets resolved."
    
    msg = "📩 *OPEN TICKETS*\n━━━━━━━━━━━━━━━━\n"
    for t in tickets:
        msg += f"🆔 {t.id} | {t.user.phone}\n"
        msg += f"💬 {t.message[:100]}\n"
        msg += "Reply: reply [ID] [MSG]\n\n"
    return msg

def reply_ticket(msg, admin_phone):
    """Reply to a support ticket and mark as replied."""
    try:
        parts = msg.split()
        if len(parts) < 3:
            return "⚠️ Usage: reply [ID] [MSG]"
        ticket_id = parts[1]
        reply_msg = " ".join(parts[2:])
        ticket = SupportTicket.get_or_none(SupportTicket.id == ticket_id)
        if not ticket:
            return f"❌ Ticket ID {ticket_id} not found."
        if ticket.status == 'replied':
            return "⚠️ Notice: This ticket was already replied."
        ticket.admin_reply = reply_msg
        ticket.status = 'replied'
        ticket.save()
        log_admin_action(admin_phone, f"Replied to ticket {ticket_id}: {reply_msg[:30]}")
        notifications.send_ticket_reply(ticket.user, reply_msg)
        return f"✅ Ticket {ticket_id} replied."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def handle_unfreeze_flow(user, msg, session):
    step = session.get('step', 1)
    cancel_words = ['cancel', 'abort', 'exit', 'stop']
    if msg.strip().lower() in cancel_words:
        return ("❌ Unfreeze process cancelled.", session, True)

    if step == 1:
        session['step'] = 2
        return ("Enter the USER ID or PHONE of the user to unfreeze:", session, False)
    elif step == 2:
        target = msg.strip()
        from database import User
        user_obj = None
        if target.isdigit():
            user_obj = User.get_or_none(User.id == int(target))
        if not user_obj:
            user_obj = User.get_or_none(User.phone == target)
        if not user_obj:
            return (f"❌ User not found for '{target}'. Type CANCEL to abort or enter a different ID/phone:", session, False)
        if not user_obj.is_frozen:
            return (f"✅ User {user_obj.id} ({user_obj.phone}) is not frozen.", session, True)
        session['target_user_id'] = user_obj.id
        session['step'] = 3
        return (f"Confirm unfreeze for User {user_obj.id} ({user_obj.phone})? Reply YES to confirm or CANCEL to abort.", session, False)
    elif step == 3:
        if msg.strip().lower() == 'yes':
            from database import User
            user_obj = User.get_or_none(User.id == session.get('target_user_id'))
            if not user_obj:
                return ("❌ User not found. Type CANCEL to abort.", session, True)
            user_obj.is_frozen = False
            user_obj.save()
            admin_phone = config.OWNER_PHONE.split(',')[0]
            log_admin_action(admin_phone, f"Unfroze user {user_obj.id} ({user_obj.phone})")
            try:
                from modules import notifications
                notifications.send_push(user_obj, "✅ Your account has been unfrozen by an admin. You may now resume normal activity.")
            except Exception:
                pass
            return (f"✅ User {user_obj.id} ({user_obj.phone}) has been unfrozen.", session, True)
        else:
            return ("❌ Unfreeze process cancelled.", session, True)
    else:
        return ("❓ Unknown step. Type CANCEL to abort.", session, False)

def handle_admin_commands(msg, user=None, session=None):
    admin_phone = None
    # You may want to extract admin_phone from context/session if needed
    # For now, assume admin_phone is available from config.OWNER_PHONE
    admin_phone = config.OWNER_PHONE.split(',')[0]
    cmd = msg.lower().split()[0]
    if cmd in ['admin', 'menu', 'help']:
        return admin_menu()
    elif cmd == 'deposits':
        return get_pending_deposits()
    elif cmd == 'users':
        return get_all_users()
    elif cmd == 'credit':
        return credit_user(msg, admin_phone)
    elif cmd == 'withdrawals':
        return get_pending_withdrawals()
    elif cmd == 'approve':
        return approve_withdrawal(msg, admin_phone)
    elif cmd == 'broadcast':
        return send_broadcast(msg, admin_phone)
    elif cmd == 'tickets':
        return get_open_tickets()
    elif cmd == 'reply':
        return reply_ticket(msg, admin_phone)
    elif cmd == 'gift':
        return get_pending_giftcards()
    elif cmd == 'unfreeze':
        # Session-based unfreeze flow
        if session is None:
            session = {}
        return handle_unfreeze_flow(user, msg, session)
    else:
        return "❓ Unknown admin command. Type 'menu' or 'help' to see all commands."