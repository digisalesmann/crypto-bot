import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

# 1. Load Environment & Config
load_dotenv()
import config
import database
import state_manager
from database import User

# 2. Import Modules (Ensure these files exist in /modules)
from modules import wallet, swap, deposit, vtu, giftcard, support, help_menu, admin, security, market, alerts, fiat, onboarding, referral

app = Flask(__name__)

# Initialize Database
try:
    database.init_db()
    print("✅ PPAY Database Connected & Online")
except Exception as e:
    print(f"❌ Database Initialization Failed: {e}")

@app.route('/bot', methods=['POST'])
def bot():
    # --- A. PARSE INCOMING DATA ---
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '').replace('whatsapp:', '')
    msg = incoming_msg.lower()
    
    # Handle Image/Media Uploads (Essential for Giftcards/Support)
    media_url = request.values.get('MediaUrl0')
    
    # 3. GET/CREATE USER
    user, _ = User.get_or_create(phone=sender)

    resp = MessagingResponse()
    response_text = ""

    # Onboarding flow for new users
    if getattr(user, 'onboarding_status', None) != 'active':
        response_text, finished = onboarding.handle_flow(user, incoming_msg)
        resp.message(response_text)
        return str(resp)

    # Identify Admin Status
    admin_list = [p.strip() for p in config.OWNER_PHONE.split(',')]
    is_admin = sender in admin_list

    # --- B. GLOBAL EXIT LOGIC ---
    if msg in ['exit', 'cancel', 'stop', 'abort']:
        state_manager.clear_all_sessions(sender)
        resp.message("❌ Operation cancelled. Type `menu` to restart.")
        return str(resp)

    # --- C. ADMIN PRIORITY ROUTING ---
    # Step-by-step admin credit/approve flows
    if is_admin:
        # Admin credit flow
        admin_credit_session = state_manager.get_session(sender, 'admin_credit')
        if (msg == 'credit' and not admin_credit_session) or admin_credit_session:
            if msg == 'credit':
                state_manager.clear_session(sender, 'admin_credit')
                session = {'step': 1}
            else:
                session = admin_credit_session or {'step': 1}
            response_text, session, done = admin.handle_credit_flow(user, incoming_msg, session)
            if done:
                state_manager.clear_session(sender, 'admin_credit')
            else:
                state_manager.set_session(sender, 'admin_credit', session)
            resp.message(response_text)
            return str(resp)
        # Admin approve flow
        admin_approve_session = state_manager.get_session(sender, 'admin_approve')
        if (msg == 'approve' and not admin_approve_session) or admin_approve_session:
            if msg == 'approve':
                state_manager.clear_session(sender, 'admin_approve')
                session = {'step': 1}
            else:
                session = admin_approve_session or {'step': 1}
            response_text, session, done = admin.handle_approve_flow(user, incoming_msg, session)
            if done:
                state_manager.clear_session(sender, 'admin_approve')
            else:
                state_manager.set_session(sender, 'admin_approve', session)
            resp.message(response_text)
            return str(resp)
        # Admin reply flow
        admin_reply_session = state_manager.get_session(sender, 'admin_reply')
        if (msg == 'reply' and not admin_reply_session) or admin_reply_session:
            if msg == 'reply':
                state_manager.clear_session(sender, 'admin_reply')
                session = {'step': 1}
            else:
                session = admin_reply_session or {'step': 1}
            response_text, session, done = admin.handle_reply_flow(user, incoming_msg, session)
            if done:
                state_manager.clear_session(sender, 'admin_reply')
            else:
                state_manager.set_session(sender, 'admin_reply', session)
            resp.message(response_text)
            return str(resp)
        # Admin broadcast flow
        admin_broadcast_session = state_manager.get_session(sender, 'admin_broadcast')
        if (msg == 'broadcast' and not admin_broadcast_session) or admin_broadcast_session:
            if msg == 'broadcast':
                state_manager.clear_session(sender, 'admin_broadcast')
                session = {'step': 1}
            else:
                session = admin_broadcast_session or {'step': 1}
            response_text, session, done = admin.handle_broadcast_flow(user, incoming_msg, session)
            if done:
                state_manager.clear_session(sender, 'admin_broadcast')
            else:
                state_manager.set_session(sender, 'admin_broadcast', session)
            resp.message(response_text)
            return str(resp)
        # Admin approve giftcard flow
        admin_approve_giftcard_session = state_manager.get_session(sender, 'approve giftcard')
        if (msg == 'approve giftcard' and not admin_approve_giftcard_session) or admin_approve_giftcard_session:
            if msg == 'approve giftcard':
                state_manager.clear_session(sender, 'approve giftcard')
                session = {'step': 1}
            else:
                session = admin_approve_giftcard_session or {'step': 1}
            response_text, session, done = admin.handle_approve_giftcard_flow(user, incoming_msg, session)
            if done:
                state_manager.clear_session(sender, 'approve giftcard')
            else:
                state_manager.set_session(sender, 'approve giftcard', session)
            resp.message(response_text)
            return str(resp)

        # Admin unfreeze flow
        admin_unfreeze_session = state_manager.get_session(sender, 'unfreeze')
        if (msg == 'unfreeze' and not admin_unfreeze_session) or admin_unfreeze_session:
            if msg == 'unfreeze':
                state_manager.clear_session(sender, 'unfreeze')
                session = {'step': 1}
            else:
                session = admin_unfreeze_session or {'step': 1}
            response_text, session, done = admin.handle_unfreeze_flow(user, incoming_msg, session)
            if done:
                state_manager.clear_session(sender, 'unfreeze')
            else:
                state_manager.set_session(sender, 'unfreeze', session)
            resp.message(response_text)
            return str(resp)

        # Fallback to legacy admin commands for other admin features
        if msg in ['admin', 'help', 'users', 'withdrawals', 'tickets', 'deposits', 'gift']:
            response = admin.handle_admin_commands(msg, user=user)
            if isinstance(response, tuple):
                response_text = response[0]
            else:
                response_text = response
            if response_text:
                resp.message(response_text)
                return str(resp)

    # --- D. MASTER SESSION ROUTER (Multi-Step Flows) ---
    active_flow = None
    flows = ['deposit', 'withdraw', 'swap', 'vtu', 'redeem', 'transfer', 'support', 'security', 'alert']
    security_aliases = ['security', 'freeze', '2fa', 'report']
    vtu_aliases = ['vtu', 'airtime', 'data']
    giftcard_aliases = ['redeem', 'giftcard']

    # Check if user is in an existing session OR starting a new one
    for flow in flows:
        if state_manager.get_session(sender, flow) or msg == flow:
            active_flow = flow
            break

    # Special handling: if user types 'airtime' or 'data', treat as VTU flow with pre-selected service
    if not active_flow and msg in vtu_aliases:
        active_flow = 'vtu'
    # Special handling: if user types 'redeem' or 'giftcard', treat as giftcard flow
    if not active_flow and msg in giftcard_aliases:
        active_flow = 'redeem'
    # Special handling: if user types 'security', 'freeze', '2fa', 'report', treat as security flow
    if not active_flow and msg in security_aliases:
        active_flow = 'security'
    # Special handling: if user types 'alert', treat as alert flow
    if not active_flow and msg.startswith('alert'):
        active_flow = 'alert'

    if active_flow:
        # Start fresh or load current step
        if msg == active_flow or (active_flow == 'vtu' and msg in vtu_aliases) or (active_flow == 'redeem' and msg in giftcard_aliases):
            state_manager.clear_all_sessions(sender)
            session = {'step': 1}
            if active_flow == 'vtu' and msg in vtu_aliases:
                session['preselected_service'] = msg
        else:
            session = state_manager.get_session(sender, active_flow)

        # Inject media_url into session if present (for gift cards/support)
        if media_url:
            session['media_url'] = media_url

        # ROUTE TO SPECIFIC MODULES
        try:
            if active_flow == 'deposit':
                response_text, session, done = deposit.handle_flow(user, incoming_msg, session)
            elif active_flow == 'withdraw':
                response_text, session, done = wallet.handle_withdraw_flow(user, incoming_msg, session)
            elif active_flow == 'swap':
                response_text, session, done = swap.handle_flow(user, incoming_msg, session)
            elif active_flow == 'vtu':
                response_text, session, done = vtu.handle_flow(user, incoming_msg, session)
            elif active_flow == 'redeem':
                response_text, session, done = giftcard.handle_flow(user, incoming_msg, session)
            elif active_flow == 'transfer':
                response_text, session, done = wallet.handle_transfer_flow(user, incoming_msg, session)
            elif active_flow == 'support':
                response_text, session, done = support.handle_flow(user, incoming_msg, session)
            elif active_flow == 'security':
                response_text, session, done = security.handle_flow(user, incoming_msg, session)
            elif active_flow == 'alert':
                response_text, session, done = alerts.handle_alert_flow(user, incoming_msg, session)
            # Save or Clear Session State
            if done:
                state_manager.clear_session(sender, active_flow)
            else:
                state_manager.set_session(sender, active_flow, session)
        except Exception as e:
            print(f"⚠️ Flow Error [{active_flow}]: {e}")
            response_text = "⚠️ An error occurred during the process. Type `cancel` and try again."
            state_manager.clear_all_sessions(sender)

    # --- E. STATIC COMMANDS & FALLBACK ---
    if not response_text:
        if msg in ['hi', 'menu', 'start']:
            response_text = help_menu.get_main_menu(user.name)
        elif msg in ['balance', 'wallet']:
            response_text = wallet.handle_balance(user)
        elif msg in ['history', 'transactions']:
            response_text = wallet.get_tx_history(user)
        elif msg == 'vtu':
            response_text = "📱 *VTU Services*\nSelect Service:\n1. Airtime\n2. Data\n\nYou can reply with the number or the name (e.g., '1' or 'airtime')."
        elif msg.startswith('price '):
            coin = msg.split(' ', 1)[1].strip()
            response_text = market.get_price(coin)
        elif msg in ['top gainers', 'gainers']:
            response_text = market.get_top_gainers()
        elif msg in ['otc', 'p2p', 'fiat']:
            response_text = fiat.get_fiat_dashboard(user)
        elif msg in ['referral', 'myreferral']:
            response_text = referral.get_referral_dashboard(user)
        else:
            response_text = "❓ Unknown command. Type `menu` to see what I can do for you."

    # --- F. FINAL RESPONSE ---
    resp.message(response_text)
    return str(resp)

if __name__ == '__main__':
    # Use 0.0.0.0 for deployment visibility
    app.run(host='0.0.0.0', port=5000, debug=False)