import csv
import datetime
from dotenv import load_dotenv

def list_pending_giftcards():
    pending = []
    try:
        with open('logs/giftcard_redemptions.log', 'r', encoding='utf-8') as f:
            for row in csv.reader(f, delimiter='\t'):
                if len(row) == 5 and row[3] == 'PENDING':
                    pending.append(row)
    except Exception as e:
        return f"⚠️ Error reading gift card log: {e}"
    if not pending or (pending[0][0].startswith('#') and len(pending) == 1):
        return '✅ No pending gift card redemptions.'
    msg = '🎁 *Pending Gift Card Redemptions:*\n'
    for row in pending:
        msg += f"• {row[0]} | {row[1]} | {row[2]} | {row[4]}\n"
    msg += '\nApprove: approve_giftcard [phone] [code] [amount]\nReject: reject_giftcard [phone] [code]'
    return msg

def update_giftcard_status(phone, code, new_status):
    updated = False
    rows = []
    with open('logs/giftcard_redemptions.log', 'r', encoding='utf-8') as f:
        for row in csv.reader(f, delimiter='\t'):
            if len(row) == 5 and row[0] == phone and row[2] == code and row[3] == 'PENDING':
                row[3] = new_status
                updated = True
            rows.append(row)
    with open('logs/giftcard_redemptions.log', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerows(rows)
    return updated
    # --- ADMIN GIFT CARD COMMANDS ---
    if is_admin and msg == 'pending_giftcards':
        response_text = list_pending_giftcards()
    elif is_admin and msg.startswith('approve_giftcard '):
        parts = msg.split(maxsplit=3)
        if len(parts) != 4:
            response_text = 'Usage: approve_giftcard [phone] [code] [amount]'
        else:
            phone, code, amount = parts[1], parts[2], parts[3]
            try:
                amount = float(amount)
            except ValueError:
                response_text = 'Invalid amount.'
                resp.message(response_text)
                return str(resp)
            # Credit wallet
            from database import Wallet, User
            try:
                user_obj = User.get(User.phone == phone)
                try:
                    wallet = Wallet.get(Wallet.user == user_obj, Wallet.currency == 'NGN')
                except Wallet.DoesNotExist:
                    response_text = f'❌ User {phone} does not have a NGN wallet. Please create one or contact support.'
                    resp.message(response_text)
                    return str(resp)
                wallet.balance += amount
                wallet.save()
                update_giftcard_status(phone, code, 'APPROVED')
                response_text = f'✅ Gift card approved and {amount:,.2f} NGN credited to {phone}.'
            except Exception as e:
                response_text = f'❌ Error crediting wallet: {e}'
    elif is_admin and msg.startswith('reject_giftcard '):
        parts = msg.split(maxsplit=2)
        if len(parts) != 3:
            response_text = 'Usage: reject_giftcard [phone] [code]'
        else:
            phone, code = parts[1], parts[2]
            if update_giftcard_status(phone, code, 'REJECTED'):
                response_text = f'❌ Gift card for {phone} ({code}) rejected.'
            else:
                response_text = 'Gift card not found or already processed.'
    elif msg.startswith('redeem '):
        # Gift card redemption: redeem [type] [code]
        parts = msg.split(maxsplit=2)
        if len(parts) < 3:
            response_text = '⚡ Usage: redeem [giftcard_type] [code]\nExample: redeem amazon ABCD-1234-EFGH\nYou can also send a card image as a follow-up message.'
        else:
            card_type = parts[1].strip().lower()
            card_code = parts[2].strip()
            # Save the request for admin review (append to DB or file, here just log for demo)
            # In production, use a GiftCardRedemption model/table
            with open('logs/giftcard_redemptions.log', 'a', encoding='utf-8') as f:
                f.write(f"{user.phone}\t{card_type}\t{card_code}\tPENDING\t{str(datetime.datetime.now())}\n")
            response_text = (
                f"🎁 Gift card submitted for review!\nType: {card_type}\nCode: {card_code}\n\n"
                "If you have a card image, please send it now as a photo. Our admin will review and credit your wallet if valid."
            )
from dotenv import load_dotenv
load_dotenv()

# DEBUG: Print loaded VTU credentials
import os
print(f"[DEBUG] VTU_USERNAME={os.getenv('VTU_USERNAME')}")
print(f"[DEBUG] VTU_PASSWORD={os.getenv('VTU_PASSWORD')}")
print(f"[DEBUG] VTU_USER_PIN={os.getenv('VTU_USER_PIN')}")
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import config
import database
from database import User
# Import ALL modules
# Import payment_methods for VTU wrappers
# Import state_manager for redeem session
from modules import market, wallet, admin, onboarding, alerts, fiat, help_menu, support, payment_methods
import state_manager
# from services.vtu_service import VTUService

app = Flask(__name__)

# Initialize DB
try:
    database.init_db()
    print("✅ System Online (Production Mode)")
except Exception as e:
    print(f"⚠️ Database Warning: {e}")

@app.route('/bot', methods=['POST'])
def bot():
    # 1. Parse Input
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '').replace('whatsapp:', '')
    msg = incoming_msg.lower()
    # 🔴 ADD THIS DEBUG PRINT
    print(f"🕵️ DEBUG: Sender='{sender}' | Admin='{config.OWNER_PHONE}' | Match? {sender == config.OWNER_PHONE}")
    resp = MessagingResponse()

    # 2. Get/Create User
    user, created = User.get_or_create(phone=sender)
    if created: user.save()

    # 3. SECURITY GATE
    if user.is_frozen and not msg.startswith('support'):
        resp.message("❄️ *ACCOUNT FROZEN*\n\nYour account has been locked for security.\nType `support` to contact admin.")
        return str(resp)

    # 4. ONBOARDING GATE
    if user.onboarding_status != 'active':
        response_text, is_finished = onboarding.handle_flow(user, msg)
        if response_text:
            resp.message(response_text)
            return str(resp)

    # 5. PRIORITY ROUTER (Admin Logic moved to TOP)
    response_text = ""
    is_admin = (sender in [p.strip() for p in config.OWNER_PHONE.split(',')])

    # --- A. ADMIN COMMANDS (Checked FIRST to prevent collisions) ---
    # We check if the sender is Admin AND if the message is an admin command
    if is_admin and (
        msg in ['admin', 'users', 'withdrawals', 'tickets'] or 
        msg.startswith(('credit', 'broadcast', 'approve', 'reply'))
    ):
        if msg == 'admin':
            response_text = help_menu.get_admin_help() + "\n• `tickets`: View Support\n• `credit`: Add funds\n• `broadcast`: Mass Msg"
        elif msg == 'users':
            response_text = admin.get_all_users()
        elif msg == 'withdrawals':
            response_text = admin.get_pending_withdrawals()
        elif msg == 'tickets':
            response_text = admin.get_open_tickets()
        elif msg.startswith('approve'):
            response_text = admin.approve_withdrawal(msg)
        elif msg.startswith('credit'):
            response_text = admin.credit_user(msg)
        elif msg.startswith('broadcast'):
            response_text = admin.send_broadcast(msg)
        elif msg.startswith('reply'):
            response_text = admin.reply_ticket(msg)

    # --- B. STANDARD USER COMMANDS ---
    # Only run if Admin didn't trigger a command above
    if not response_text:
        

        # --- Deposit Session-Based Flow ---

        if msg.startswith('deposit') or state_manager.get_deposit_session(user.phone):
            if msg.startswith('deposit'):
                print('[DEBUG] Clearing other sessions for deposit flow')
                state_manager.clear_withdraw_session(user.phone)
                state_manager.clear_swap_session(user.phone)
                state_manager.clear_redeem_session(user.phone)
            session = state_manager.get_deposit_session(user.phone) or {
                'step': 0, 'type': None, 'coin': None, 'chain': None, 'method': None
            }
            # ...existing code for deposit session flow...
            # (Unchanged, see above)
            # ...existing code...
            # Call your deposit session handler here if you have one:
            from modules import deposit
            # Always use the handler (now implemented)
            response_text, session, done = deposit.handle_flow(user, incoming_msg, session)
            if done:
                state_manager.clear_deposit_session(user.phone)
            else:
                state_manager.set_deposit_session(user.phone, session)

        # --- Withdraw Session-Based Flow ---
        elif msg.startswith('withdraw') or state_manager.get_withdraw_session(user.phone):
            if msg.startswith('withdraw'):
                print('[DEBUG] Clearing other sessions for withdraw flow')
                state_manager.clear_deposit_session(user.phone)
                state_manager.clear_swap_session(user.phone)
                state_manager.clear_redeem_session(user.phone)
        # --- Swap Session-Based Flow ---
        elif msg.startswith('swap') or state_manager.get_swap_session(user.phone):
            if msg.startswith('swap'):
                print('[DEBUG] Clearing other sessions for swap flow')
                state_manager.clear_deposit_session(user.phone)
                state_manager.clear_withdraw_session(user.phone)
                state_manager.clear_redeem_session(user.phone)
            from modules import swap
            session = state_manager.get_swap_session(user.phone) or swap.start_swap_session(user)
            def price_lookup(from_asset, to_asset):
                # Try fiat.get_rates first for fiat/crypto pairs
                try:
                    from modules import fiat
                    buy_rate, sell_rate = fiat.get_rates(from_asset, to_asset)
                    if buy_rate:
                        return buy_rate
                except Exception:
                    pass
                # Try exchange for crypto/crypto
                try:
                    from services import exchange
                    symbol = f"{from_asset}/{to_asset}"
                    return exchange.get_price(symbol)
                except Exception:
                    return None
            response_text, session, done = swap.handle_swap_flow(user, incoming_msg, session, price_lookup)
            if done:
                state_manager.clear_swap_session(user.phone)
            else:
                state_manager.set_swap_session(user.phone, session)

            session = state_manager.get_withdraw_session(user.phone) or {
                'step': 0, 'asset': None, 'amount': None, 'destination': None, 'chain': None, 'method': None, 'account_name': None
            }
            # Step 0: Start
            if session['step'] == 0:
                session['step'] = 1
                state_manager.set_withdraw_session(user.phone, session)
                response_text = 'What asset would you like to withdraw? (e.g. USDT, BTC, NGN)'
            # Step 1: Asset
            elif session['step'] == 1:
                asset = incoming_msg.strip().upper()
                session['asset'] = asset
                # Check if crypto or fiat
                from modules.bybit_client import SUPPORTED_COINS
                if asset in SUPPORTED_COINS:
                    session['type'] = 'crypto'
                    session['step'] = 2
                    state_manager.set_withdraw_session(user.phone, session)
                    response_text = f'How much {asset} would you like to withdraw?'
                elif asset == 'NGN':
                    session['type'] = 'fiat'
                    session['step'] = 2
                    state_manager.set_withdraw_session(user.phone, session)
                    response_text = 'How much NGN would you like to withdraw?'
                else:
                    response_text = 'Unsupported asset. Please enter a supported coin (e.g. USDT, BTC, ETH, BNB, SOL) or NGN.'
            # Step 2: Amount
            elif session['step'] == 2:
                try:
                    amount = float(incoming_msg.strip().replace(',', ''))
                    if amount <= 0:
                        response_text = 'Amount must be greater than zero.'
                    else:
                        session['amount'] = amount
                        if session.get('type') == 'crypto':
                            session['step'] = 3
                            state_manager.set_withdraw_session(user.phone, session)
                            from modules.bybit_client import SUPPORTED_CHAINS
                            chains = ', '.join(SUPPORTED_CHAINS.get(session['asset'], []))
                            response_text = f'Which chain for {session["asset"]}? Supported: {chains}'
                        else:
                            session['step'] = 4
                            state_manager.set_withdraw_session(user.phone, session)
                            response_text = 'Please enter your bank details in the format: [AccountNumber_BankName] (e.g. 0012345678_GTBank)'
                except ValueError:
                    response_text = 'Invalid amount. Please enter a number.'
            # Step 3: Chain (crypto)
            elif session['step'] == 3:
                chain = incoming_msg.strip().upper()
                from modules.bybit_client import SUPPORTED_CHAINS
                if chain not in SUPPORTED_CHAINS.get(session['asset'], []):
                    chains = ', '.join(SUPPORTED_CHAINS.get(session['asset'], []))
                    response_text = f'⚠️ {chain} is not supported for {session["asset"]}. Supported: {chains}'
                else:
                    session['chain'] = chain
                    session['step'] = 4
                    state_manager.set_withdraw_session(user.phone, session)
                    response_text = f'Please enter the {session["asset"]} address for {chain}.'
            # Step 4: Destination (crypto address or bank)
            elif session['step'] == 4:
                if session.get('type') == 'crypto':
                    session['destination'] = incoming_msg.strip()
                    # Show summary and ask for confirmation
                    summary = (
                        f"Please confirm your withdrawal:\n"
                        f"Asset: {session['asset']}\n"
                        f"Amount: {session['amount']}\n"
                        f"Chain: {session['chain']}\nAddress: {session['destination']}\n"
                    )
                    summary += '\nType "yes" to confirm or "no" to cancel.'
                    session['step'] = 5
                    state_manager.set_withdraw_session(user.phone, session)
                    response_text = summary
                else:
                    session['destination'] = incoming_msg.strip()
                    session['step'] = 4.5
                    state_manager.set_withdraw_session(user.phone, session)
                    response_text = 'Please enter the account holder name for this bank account:'
            # Step 4.5: Account holder name (fiat)
            elif session['step'] == 4.5:
                session['account_name'] = incoming_msg.strip()
                # Show summary and ask for confirmation
                summary = (
                    f"Please confirm your withdrawal:\n"
                    f"Asset: {session['asset']}\n"
                    f"Amount: {session['amount']}\n"
                    f"Bank: {session['destination']}\n"
                    f"Account Name: {session['account_name']}\n"
                )
                summary += '\nType "yes" to confirm or "no" to cancel.'
                session['step'] = 5
                state_manager.set_withdraw_session(user.phone, session)
                response_text = summary
            # Step 5: Confirmation
            elif session['step'] == 5:
                if incoming_msg.strip().lower() in ['yes', 'y']:
                    # Process withdrawal
                    from modules import wallet
                    if session.get('type') == 'crypto':
                        # Compose command: withdraw [ASSET] [AMOUNT] [ADDRESS] [CHAIN]
                        cmd = f"withdraw {session['asset']} {session['amount']} {session['destination']} {session['chain']}"
                    else:
                        # Compose command: withdraw NGN [AMOUNT] [BANK] [ACCOUNT_NAME]
                        cmd = f"withdraw NGN {session['amount']} {session['destination']} {session['account_name']}"
                    response_text = wallet.handle_withdrawal(user, cmd)
                    state_manager.clear_withdraw_session(user.phone)
                elif incoming_msg.strip().lower() in ['no', 'n', 'cancel']:
                    state_manager.clear_withdraw_session(user.phone)
                    response_text = 'Withdrawal cancelled.'
                else:
                    response_text = 'Please type "yes" to confirm or "no" to cancel.'
            else:
                response_text = '❓ Unknown step in withdraw flow. Type `withdraw` to restart.'

        # Navigation
        elif msg in ['menu', 'hi', 'start']:
            response_text = (
                f"👋 Hello *{user.name}*!\n"
                "Welcome to the OTC Trading Desk.\n\n"
                "💰 *Balance:* Type `balance`\n"
                "💱 *Trade:* Type `otc`\n"
                "❓ *Commands:* Type `help`\n"
            )
        elif msg == 'help':
            help_text = help_menu.get_help_text()
            # Twilio/WhatsApp message limit (safe value)
            CHUNK_SIZE = 1500
            if len(help_text) > CHUNK_SIZE:
                for i in range(0, len(help_text), CHUNK_SIZE):
                    resp.message(help_text[i:i+CHUNK_SIZE])
                return str(resp)
            else:
                response_text = help_text


        # Gift Card Redemption (step-by-step)
        elif msg.startswith('redeem') or state_manager.get_redeem_session(user.phone):
            if msg.startswith('redeem'):
                print('[DEBUG] Clearing other sessions for redeem flow')
                state_manager.clear_deposit_session(user.phone)
                state_manager.clear_withdraw_session(user.phone)
                state_manager.clear_swap_session(user.phone)
            session = state_manager.get_redeem_session(user.phone) or {
                'step': 0, 'type': None, 'code': None, 'country': None, 'amount': None, 'cardmode': None, 'image': None
            }
            # If just starting
            if session['step'] == 0:
                session['step'] = 1
                state_manager.set_redeem_session(user.phone, session)
                response_text = 'Please enter the card type (e.g. Amazon, iTunes, Steam):'
            elif session['step'] == 1:
                session['type'] = incoming_msg.strip()
                session['step'] = 2
                state_manager.set_redeem_session(user.phone, session)
                response_text = 'Please enter the card code:'
            elif session['step'] == 2:
                session['code'] = incoming_msg.strip()
                session['step'] = 3
                state_manager.set_redeem_session(user.phone, session)
                response_text = 'Please enter the card country:'
            elif session['step'] == 3:
                session['country'] = incoming_msg.strip()
                session['step'] = 4
                state_manager.set_redeem_session(user.phone, session)
                response_text = 'Please enter the card amount:'
            elif session['step'] == 4:
                session['amount'] = incoming_msg.strip()
                session['step'] = 5
                state_manager.set_redeem_session(user.phone, session)
                response_text = 'Is this card an ecode or physical card? (Type "ecode" or "physical"):'
            elif session['step'] == 5:
                session['cardmode'] = incoming_msg.strip().lower()
                session['step'] = 6
                state_manager.set_redeem_session(user.phone, session)
                response_text = 'If you have a card image, please send it now or type "skip" to continue:'
            elif session['step'] == 6:
                # WhatsApp image/media handling
                media_url = request.values.get('MediaUrl0')
                if media_url and incoming_msg.strip().lower() == 'skip':
                    # User typed skip but sent an image, prefer image
                    session['image'] = media_url
                elif media_url:
                    session['image'] = media_url
                elif incoming_msg.strip().lower() != 'skip':
                    session['image'] = incoming_msg.strip()
                # Save to log
                with open('logs/giftcard_redemptions.log', 'a', encoding='utf-8') as f:
                    f.write(f"{user.phone}\t{session['type']}\t{session['code']}\tPENDING\t{str(datetime.datetime.now())}\t{session['country']}\t{session['amount']}\t{session['cardmode']}\t{session.get('image','')}\n")
                # Notify admins
                try:
                    from modules import notifications
                    admin_phones = [p.strip() for p in config.OWNER_PHONE.split(',')]
                    admin_msg = (
                        f"[NEW GIFT CARD REDEEM]\nUser: {user.phone}\nType: {session['type']}\nCode: {session['code']}\nCountry: {session['country']}\nAmount: {session['amount']}\nMode: {session['cardmode']}\n"
                        + (f"Image: {session['image']}\n" if session.get('image') else '')
                        + f"Time: {str(datetime.datetime.now())}"
                    )
                    for admin_phone in admin_phones:
                        notifications.send_push(type('AdminUser', (), {'phone': admin_phone}), admin_msg)
                except Exception as e:
                    print(f"[ERROR] Failed to notify admins: {e}")
                state_manager.clear_redeem_session(user.phone)
                response_text = (
                    f"🎁 Gift card submitted for review!\nType: {session['type']}\nCode: {session['code']}\nCountry: {session['country']}\nAmount: {session['amount']}\nMode: {session['cardmode']}\n"
                    + (f"Image: {session['image']}\n" if session.get('image') else '')
                    + "\nIf you have a card image, you can also send it as a photo. Our admin will review and credit your wallet if valid."
                )

        # Market
        elif msg.startswith('price'):
            parts = msg.split()
            if len(parts) > 1: response_text = market.get_price(parts[1])
            else: response_text = "⚠️ Usage: `price BTC`"
        elif 'top' in msg:
            response_text = market.get_top_gainers()
        elif msg.startswith('alert'):
            if msg == 'alerts': response_text = alerts.get_my_alerts(user)
            else: response_text = alerts.create_alert(user, msg)

        # Wallet
        elif msg in ['balance', 'wallet']:
            try:
                response_text = wallet.handle_balance(user)
            except Exception as e:
                if 'DoesNotExist' in str(e):
                    response_text = '❌ You do not have a wallet. Please contact support.'
                else:
                    print(f"[ERROR] handle_balance failed: {e}")
                    response_text = "⚠️ Error fetching balance. Please try again later."
        elif msg.startswith('deposit'):
            parts = msg.split()
            # deposit (show all options)
            if len(parts) == 1:
                crypto_coins = ['USDT', 'BTC', 'ETH', 'SOL', 'BNB']
                crypto_chains = ['BEP20', 'BNB', 'BTC', 'ERC20', 'SOL', 'TRC20']
                methods = ', '.join(fiat.list_fiat_methods())
                response_text = (
                    "🏦 *Deposit Options*\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "Send supported coins to your CEX Master Wallet.\n\n"
                    f"*Supported Coins:* {', '.join(crypto_coins)}\n"
                    f"*Supported Chains:* {', '.join(crypto_chains)}\n\n"
                    "Type `deposit [COIN] [CHAIN]` for a specific address.\n"
                    "Example: `deposit BTC BTC` or `deposit USDT TRC20`\n\n"
                    "💳 *Supported Fiat Methods:*\n"
                    f"{methods}\n"
                    "Type `deposit [method]` for details."
                )
            # deposit bank or deposit bank transfer (fiat)
            elif len(parts) == 2 and parts[1].replace(' ', '').lower() in ['bank', 'banktransfer']:
                response_text = fiat.get_fiat_deposit_info('bank')
            # deposit [METHOD] (fiat/off-chain)
            elif len(parts) == 2 and parts[1].lower() in [m.lower().replace(' ', '') for m in fiat.list_fiat_methods()]:
                # Normalize method for lookup
                method_key = parts[1].replace(' ', '').lower()
                if method_key == 'banktransfer':
                    method_key = 'bank'
                response_text = fiat.get_fiat_deposit_info(method_key)
            # deposit [COIN] [CHAIN] (crypto)
            elif len(parts) == 3:
                response_text = wallet.get_deposit_address_dynamic(user, parts[1], parts[2])
            # deposit methods (list all)
            elif len(parts) == 2 and parts[1].lower() == 'methods':
                methods = ', '.join(fiat.list_fiat_methods())
                response_text = f"💳 *Supported Deposit Methods:*\n{methods}\nType `deposit [method]` for details."
            else:
                response_text = wallet.get_deposit_address(user)
        elif msg.startswith('withdraw'):
            response_text = wallet.handle_withdrawal(user, msg)
        elif msg in ['history', 'transactions']:
            response_text = wallet.get_tx_history(user)

        elif msg.startswith('transfer'):
            response_text = wallet.handle_internal_transfer(user, msg)

        # Direct VTU commands
        elif msg.startswith('airtime '):
            parts = msg.split()
            if len(parts) == 4:
                network = parts[1]
                phone = parts[2]
                try:
                    amount = float(parts[3])
                except ValueError:
                    response_text = '⚠️ Invalid amount.'
                    resp.message(response_text)
                    return str(resp)
                if amount < 100:
                    response_text = '⚠️ Minimum airtime top-up is 100 NGN.'
                    resp.message(response_text)
                    return str(resp)
                # Production-grade NGN wallet balance check
                from database import Wallet
                try:
                    # CHANGED: wallet → user_wallet to avoid name collision
                    user_wallet, _ = Wallet.get_or_create(user=user, currency='NGN', defaults={'balance': 0})
                except Exception as e:
                    print(f"[ERROR] Failed to get or create wallet: {e}")
                    response_text = '❌ System error: Could not access your NGN wallet. Please contact support.'
                    resp.message(response_text)
                    return str(resp)
                # CHANGED: wallet → user_wallet
                if user_wallet.balance < amount:
                    response_text = f'❌ Insufficient NGN balance. You have {user_wallet.balance:,.2f} NGN.'
                    resp.message(response_text)
                    return str(resp)
                # Use the production-ready wrapper
                try:
                    result = payment_methods.buy_airtime(user.id if hasattr(user, 'id') else user.phone, phone, network, amount)
                except Exception as e:
                    print(f"[ERROR] VTU buy_airtime exception: {e}")
                    response_text = f"❌ VTU Error: {str(e)}"
                    resp.message(response_text)
                    return str(resp)
                if result and result.get('code') == 'success':
                    try:
                        # CHANGED: wallet → user_wallet
                        user_wallet.balance -= amount
                        user_wallet.save()
                        response_text = f"✅ Airtime top-up successful! {amount:,.2f} NGN sent to {phone} ({network})."
                    except Exception as e:
                        print(f"[ERROR] Failed to deduct wallet after VTU: {e}")
                        response_text = f"✅ Airtime top-up successful, but failed to update wallet. Please contact support."
                else:
                    response_text = f"❌ VTU Error: {result.get('message', 'Unknown error')}"
            else:
                response_text = 'Usage: airtime [network] [phone] [amount]'

        elif msg.startswith('tv '):
            parts = msg.split()
            if len(parts) == 4:
                provider = parts[1]
                card = parts[2]
                plan_id = parts[3]
                response_text = '❌ VTUService.process_tv_payment is deprecated. Please use the new VTUApiClient wrappers.'
            else:
                response_text = 'Usage: tv [provider] [card] [plan_id]'

        elif msg.startswith('epins '):
            parts = msg.split()
            if len(parts) == 4:
                network = parts[1]
                value = parts[2]
                qty = parts[3]
                response_text = '❌ VTUService.process_epins_purchase is deprecated. Please use the new VTUApiClient wrappers.'
            else:
                response_text = 'Usage: epins [network] [value] [qty]'

        elif msg.startswith('betting '):
            parts = msg.split()
            if len(parts) == 4:
                provider = parts[1]
                account = parts[2]
                try:
                    amount = float(parts[3])
                except ValueError:
                    response_text = '⚠️ Invalid amount.'
                    resp.message(response_text)
                    return str(resp)
                response_text = '❌ VTUService.process_betting_fund is deprecated. Please use the new VTUApiClient wrappers.'
            else:
                response_text = 'Usage: betting [provider] [account] [amount]'

        # Legacy VTU command
        elif msg.startswith('vtu'):
            parts = msg.split()
            if len(parts) >= 2:
                vtu_type = parts[1]
                if vtu_type == 'airtime' and len(parts) == 5:
                    phone = parts[2]
                    try:
                        amount = float(parts[3])
                    except ValueError:
                        response_text = '⚠️ Invalid amount.'
                        resp.message(response_text)
                        return str(resp)
                    network = parts[4]
                    response_text = '❌ VTUService.process_airtime_topup is deprecated. Please use the new VTUApiClient wrappers.'
                elif vtu_type == 'data' and len(parts) == 5:
                    phone = parts[2]
                    plan_id = parts[3]
                    network = parts[4]
                    response_text = '❌ VTUService.process_data_topup is deprecated. Please use the new VTUApiClient wrappers.'
                else:
                    response_text = (
                        '⚡ *VTU Services*\n'
                        'Usage:\n'
                        '`vtu airtime [phone] [amount] [network]`\n'
                        '`vtu data [phone] [plan_id] [network]`'
                    )
            else:
                response_text = (
                    '⚡ *VTU Services*\n'
                    'Usage:\n'
                    '`vtu airtime [phone] [amount] [network]`\n'
                    '`vtu data [phone] [plan_id] [network]`'
                )

        # OTC
        elif msg.startswith('swap'):
            # Fallback: direct swap command (old style)
            from modules import fiat
            response_text = fiat.execute_swap(user, msg)
        elif msg in ['otc', 'p2p']:
            response_text = fiat.get_fiat_dashboard(user)

        # Support
        elif msg == 'support':
            response_text = (
                "☎️ *Contact Support*\n"
                "━━━━━━━━━━━━━━━━\n"
                "• Admin: wa.me/+2349037884753\n"
                "• Admin: wa.me/+2349037978457\n"
                "• Email: buildwithvictorhq@gmail.com\n"
                "• Email: ppay.ng1@gmail.com\n\n"
                "📝 *Open a Ticket:*\n"
                "Type `support [Your Message]`\n"
                "Ex: `support I deposited 500 NGN`"
            )
        elif msg.startswith('support '):
            response_text = support.create_ticket(user, msg)
        elif msg in ['tickets', 'ticket']:
            response_text = support.get_my_tickets(user)
        elif msg in ['security', 'freeze', '2fa', 'report']:
            response_text = support.security_center(user, msg)

        # Fallback
        else:
            print('[DEBUG] Unknown command or no session matched')
            response_text = "❓ Unknown command. Type `help`."

    print(f"[DEBUG] Response to user: {response_text}")
    resp.message(response_text)
    twilio_xml = str(resp)
    print(f"[DEBUG] Twilio XML to send: {twilio_xml}")
    return twilio_xml

if __name__ == '__main__':
    # Production: Debug=False, Host=0.0.0.0
    app.run(host='0.0.0.0', port=5000, debug=False)