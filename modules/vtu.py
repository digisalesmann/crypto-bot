import uuid
import threading
import config
from database import Wallet, db, Transaction
from modules import notifications

def handle_flow(user, msg, session):
    # Block if account is frozen
    if getattr(user, 'is_frozen', False):
        return ("❄️ Your account is currently frozen. VTU services are disabled. Contact support to unfreeze.", session, True)

    step = session.get('step')
    msg_clean = msg.strip().lower()

    # --- EXIT LOGIC ---
    if msg_clean in ['exit', 'cancel', 'stop']:
        return "❌ VTU session cancelled.", session, True

    # Step 1: Service Selection
    if step == 1:
        preselected = session.get('preselected_service')
        opts = "📱 *VTU Services*\nSelect Service:\n1. Airtime\n2. Data\n\nReply with number or name."

        if preselected == 'airtime':
            session['service'] = "Airtime"
            session['step'] = 21
            return "Select Network Provider for Airtime:\n1. MTN\n2. Airtel\n3. Glo\n4. 9mobile", session, False
        elif preselected == 'data':
            session['service'] = "Data"
            session['step'] = 22
            return "Select Network Provider for Data:\n1. MTN\n2. Airtel\n3. Glo\n4. 9mobile", session, False
        else:
            session['step'] = 2
            return opts, session, False

    # Step 2: Manual Service Selection
    if step == 2:
        if msg_clean in ['1', 'airtime']:
            session['service'] = "Airtime"
            session['step'] = 21
            return "Select Network Provider for Airtime:\n1. MTN\n2. Airtel\n3. Glo\n4. 9mobile", session, False
        elif msg_clean in ['2', 'data']:
            session['service'] = "Data"
            session['step'] = 22
            return "Select Network Provider for Data:\n1. MTN\n2. Airtel\n3. Glo\n4. 9mobile", session, False
        else:
            return "❓ Please select '1' for Airtime or '2' for Data.", session, False

    # Step 21: Airtime Network Selection
    if step == 21:
        provider_map = {'1': 'MTN', '2': 'Airtel', '3': 'Glo', '4': '9mobile', 'mtn': 'MTN', 'airtel': 'Airtel', 'glo': 'Glo', '9mobile': '9mobile'}
        provider = provider_map.get(msg_clean)
        if not provider:
            return "❓ Invalid provider. Select MTN, Airtel, Glo, or 9mobile.", session, False
        session['provider'] = provider
        session['step'] = 3
        return f"Enter Recipient Phone Number for {provider} Airtime:", session, False

    # Step 22: Data Network Selection
    if step == 22:
        provider_map = {'1': 'MTN', '2': 'Airtel', '3': 'Glo', '4': '9mobile', 'mtn': 'MTN', 'airtel': 'Airtel', 'glo': 'Glo', '9mobile': '9mobile'}
        provider = provider_map.get(msg_clean)
        if not provider:
            return "❓ Invalid provider. Select MTN, Airtel, Glo, or 9mobile.", session, False
        session['provider'] = provider
        session['step'] = 23
        return f"Select Data Plan for {provider}:\n1. 500MB\n2. 1GB\n3. 2GB\n4. 5GB", session, False

    # Step 23: Data Plan Price Lookup
    if step == 23:
        plan_map = {'1': '500MB', '2': '1GB', '3': '2GB', '4': '5GB', '500mb': '500MB', '1gb': '1GB', '2gb': '2GB', '5gb': '5GB'}
        plan = plan_map.get(msg_clean)
        if not plan:
            return "❓ Invalid plan. Please select 500MB, 1GB, 2GB, or 5GB.", session, False

        session['plan'] = plan
        try:
            from services import vtu_service
            # Data plan lookup logic
            price, variation_id = vtu_service.get_data_plan_price(session['provider'], plan)
            if price is None:
                return f"⚠️ Could not fetch price for {plan}. Try again later.", session, True

            session['plan_price'] = price
            session['variation_id'] = variation_id
            session['step'] = 3
            return f"Price for {plan}: ₦{price}\nEnter Recipient Phone Number:", session, False
        except Exception as e:
            return f"⚠️ Price lookup error: {e}", session, True

    # Step 3: Recipient Phone Number
    if step == 3:
        session['target'] = msg.strip()
        if session.get('service') == 'Data':
            session['step'] = 4
            return f"Confirm: Buy {session['plan']} Data for {session['target']} at ₦{session['plan_price']}? (Type 'yes' to proceed)", session, False
        else:
            session['step'] = 3.5
            return "Enter Airtime Amount (NGN):", session, False

    # Step 3.5: Airtime Amount
    if step == 3.5:
        try:
            amount = int(msg.strip())
            if amount < 100:
                return "⚠️ Minimum airtime is ₦100.", session, False
            session['amount'] = amount
            session['step'] = 4
            return f"Confirm: Buy ₦{amount} Airtime for {session['target']}? (Type 'yes' to proceed)", session, False
        except ValueError:
            return "❌ Please enter a valid number.", session, False

    # Step 4: Final Execution
    if step == 4:
        if msg_clean != 'yes':
            return "❌ Transaction cancelled.", session, True

        service = session.get('service')
        amount = int(session.get('amount') if service == 'Airtime' else session.get('plan_price', 0))

        # 1. Wallet Check
        try:
            user_wallet = Wallet.get(Wallet.user == user, Wallet.currency == 'NGN')
            if user_wallet.balance < amount:
                return f"❌ Insufficient NGN balance (₦{user_wallet.balance:,.2f}).", session, True
        except Wallet.DoesNotExist:
            return "❌ NGN Wallet not found.", session, True

        # 2. Execute Transaction
        try:
            from services.vtu_service import VTUApiClient
            vtu_client = VTUApiClient()
            request_id = f"req_{uuid.uuid4().hex[:12]}"
            provider_id = session.get('provider').lower()

            with db.atomic():
                user_wallet.balance -= amount
                user_wallet.save()
                tx = Transaction.create(user=user, type=f'VTU_{service.upper()}', currency='NGN', amount=amount, status='pending', tx_hash=session['target'])

            if service == 'Airtime':
                resp = vtu_client.purchase_airtime(request_id, session['target'], provider_id, amount)
            else:
                resp = vtu_client.purchase_data(request_id, session['target'], provider_id, session['variation_id'])

            if resp.get('status') == 'success' or 'success' in resp.get('message', '').lower():
                tx.status = 'completed'
                tx.save()
                # Admin Notification
                notifications.send_push(type('Admin', (), {'phone': config.OWNER_PHONE.split(',')[0]}), f"📱 VTU SUCCESS: {user.phone} bought {service} for {session['target']}")
                return f"✅ {service} successful! ₦{amount} has been sent to {session['target']}.", session, True
            else:
                # Refund logic if API fails
                with db.atomic():
                    user_wallet.balance += amount
                    user_wallet.save()
                    tx.status = 'failed'
                    tx.save()
                return f"❌ VTU Provider Error: {resp.get('message', 'Unknown error')}. Balance refunded.", session, True

        except Exception as e:
            return f"❌ System Error: {e}", session, True

    return "❓ Unknown step. Type 'menu' to restart.", session, True