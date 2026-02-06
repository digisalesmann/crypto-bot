from database import User, Wallet, Transaction, SupportTicket, db
from modules import notifications
import config

def get_all_users():
    """
    Lists all users registered in the bot.
    """
    users = User.select()
    report = "👥 *User Base:*\n━━━━━━━━━━━━━━━━\n"
    for u in users:
        status = "❄️" if u.is_frozen else "✅"
        report += f"{status} {u.phone} (Level {u.kyc_level})\n"
    return report

def credit_user(msg):
    """
    Usage: credit [PHONE] [AMOUNT] [CURRENCY]
    Ex: credit +23490... 100 USDT
    """
    try:
        parts = msg.split()
        target_phone = parts[1]
        amount = float(parts[2])
        currency = parts[3].upper()

        # 1. Find User
        target_user = User.get_or_none(User.phone == target_phone)
        if not target_user:
            return "❌ User not found. Ask them to say 'Hi' to the bot first."

        # 2. Update Wallet (Atomic Transaction)
        with db.atomic():
            wallet, created = Wallet.get_or_create(user=target_user, currency=currency)
            wallet.balance += amount
            wallet.save()

            # Log Transaction
            Transaction.create(
                user=target_user,
                type='DEPOSIT',  # Marked as standard deposit
                currency=currency,
                amount=amount,
                status='completed',
                tx_hash='ADMIN_CREDIT'
            )

        # 3. Trigger Notification
        notifications.send_deposit_confirmation(target_user, amount, currency)

        return f"✅ SUCCESS: Added {amount} {currency} to {target_user.name} and sent notification."

    except IndexError:
        return "⚠️ Usage: credit <PHONE> <AMOUNT> <CURRENCY>"
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def send_broadcast(msg):
    """
    Usage: broadcast [MESSAGE]
    Sends a message to ALL users.
    """
    # Remove the word 'broadcast'
    announcement = msg.replace('broadcast', '', 1).strip()
    
    if len(announcement) < 5:
        return "⚠️ Announcement too short. Usage: `broadcast [Message]`"
        
    result = notifications.broadcast_all(announcement)
    return result

def get_pending_withdrawals():
    """
    Lists all withdrawals waiting for approval.
    """
    pending = Transaction.select().where(
        (Transaction.type == 'WITHDRAWAL') & 
        (Transaction.status == 'pending')
    )
    
    if not pending:
        return "✅ No pending withdrawals."
        
    msg = "🕵️ *Pending Approvals*\n"
    for tx in pending:
        msg += f"ID `{tx.id}`: {tx.amount} {tx.currency}\n"
        msg += f"User: {tx.user.phone}\n"
        msg += f"Dest: `{tx.tx_hash}`\n\n" 
        
    msg += "To mark paid: `approve [ID] [REF_CODE]`"
    return msg

def approve_withdrawal(msg):
    """
    Usage: approve [ID] [TX_HASH/REF]
    Updates status to completed and notifies user.
    """
    try:
        parts = msg.split()
        tx_id = parts[1]
        real_tx_hash = " ".join(parts[2:]) # Captures "GTB Ref 123..."
        
        tx = Transaction.get(Transaction.id == tx_id)
        
        if tx.status == 'completed':
            return "⚠️ Transaction already completed."
            
        tx.status = 'completed'
        tx.tx_hash = real_tx_hash
        tx.save()
        
        # 🔔 Notify User
        notifications.send_withdrawal_processed(tx.user, tx.amount, tx.currency, real_tx_hash)
        
        return f"✅ Withdrawal {tx_id} approved & User notified."
    except Exception as e:
        return f"⚠️ Error. Usage: `approve [ID] [REF]`"

def get_open_tickets():
    tickets = SupportTicket.select().where(SupportTicket.status == 'open')
    if not tickets: return "✅ No open tickets."
    
    msg = "📩 *Open Support Tickets*\n"
    for t in tickets:
        msg += f"🆔 {t.id} | 👤 {t.user.phone}\n"
        msg += f"📝 {t.message}\n"
        msg += "To reply: `reply [ID] [MESSAGE]`\n\n"
    return msg

def reply_ticket(msg):
    """
    Usage: reply [ID] [MESSAGE]
    """
    try:
        parts = msg.split()
        ticket_id = parts[1]
        reply_text = " ".join(parts[2:])
        
        t = SupportTicket.get(SupportTicket.id == ticket_id)
        t.admin_reply = reply_text
        t.status = 'replied'
        t.save()
        
        # 🔔 Notify User (Optional: You can add a specific notification function for this)
        notifications.send_push(t.user, f"📩 *Support Reply:*\n{reply_text}")
        
        return f"✅ Replied to Ticket #{ticket_id}"
    except:
        return "⚠️ Error. Usage: `reply [ID] [TEXT]`"