# modules/vtu.py
def handle_flow(user, msg, session):
    step = session.get('step')
    # If preselected_service is set (from 'airtime' or 'data' command), skip service selection
    if step == 1:
        preselected = session.get('preselected_service')
        opts = "📱 *VTU Services*\nSelect Service:\n1. Airtime\n2. Data\n\nYou can reply with the number or the name (e.g., '1' or 'airtime')."
        if preselected:
            # Set service and go to provider selection, not phone number
            if preselected == 'airtime':
                session['service'] = "Airtime"
                session['step'] = 21
                return "Select Network Provider for Airtime:\n1. MTN\n2. Airtel\n3. Glo\n4. 9mobile\n\nReply with the number or name.", session, False
            elif preselected == 'data':
                session['service'] = "Data"
                session['step'] = 22
                return "Select Network Provider for Data:\n1. MTN\n2. Airtel\n3. Glo\n4. 9mobile\n\nReply with the number or name.", session, False
        else:
            session['step'] = 2
            return opts, session, False

    if step == 2:
        msg_clean = msg.strip().lower()
        if msg_clean in ['1', 'airtime']:
            session['service'] = "Airtime"
            session['step'] = 21
            # Prompt for provider selection for airtime
            return "Select Network Provider for Airtime:\n1. MTN\n2. Airtel\n3. Glo\n4. 9mobile\n\nReply with the number or name.", session, False
        elif msg_clean in ['2', 'data']:
            session['service'] = "Data"
            session['step'] = 22
            # Prompt for provider selection for data
            return "Select Network Provider for Data:\n1. MTN\n2. Airtel\n3. Glo\n4. 9mobile\n\nReply with the number or name.", session, False
        else:
            return "❓ Please reply with '1' or 'airtime' for Airtime, or '2' or 'data' for Data.", session, False

    # Airtime provider selection
    if step == 21:
        provider_map = {'1': 'MTN', '2': 'Airtel', '3': 'Glo', '4': '9mobile', 'mtn': 'MTN', 'airtel': 'Airtel', 'glo': 'Glo', '9mobile': '9mobile'}
        msg_clean = msg.strip().lower()
        provider = provider_map.get(msg_clean)
        if not provider:
            return "❓ Please reply with the number or name of the provider (e.g., '1' or 'MTN').", session, False
        session['provider'] = provider
        session['step'] = 3
        return f"Enter Recipient Phone Number for {provider} Airtime:", session, False

    # Data provider selection
    if step == 22:
        provider_map = {'1': 'MTN', '2': 'Airtel', '3': 'Glo', '4': '9mobile', 'mtn': 'MTN', 'airtel': 'Airtel', 'glo': 'Glo', '9mobile': '9mobile'}
        msg_clean = msg.strip().lower()
        provider = provider_map.get(msg_clean)
        if not provider:
            return "❓ Please reply with the number or name of the provider (e.g., '1' or 'MTN').", session, False
        session['provider'] = provider
        session['step'] = 23
        # Prompt for data plan selection
        return f"Select Data Plan for {provider}:\n1. 500MB\n2. 1GB\n3. 2GB\n4. 5GB\n\nReply with the number or plan (e.g., '1' or '500MB').", session, False

    # Data plan selection
    if step == 23:
        plan_map = {'1': '500MB', '2': '1GB', '3': '2GB', '4': '5GB', '500mb': '500MB', '1gb': '1GB', '2gb': '2GB', '5gb': '5GB'}
        msg_clean = msg.strip().lower()
        plan = plan_map.get(msg_clean)
        if not plan:
            return "❓ Please reply with the number or name of the plan (e.g., '1' or '500MB').", session, False
        session['plan'] = plan
        # --- Fetch live price and variation_id from vtu.ng ---
        try:
            from services import vtu_service
            # Add a timeout to avoid hanging
            import threading
            result = {}
            def fetch_price():
                try:
                    price, variation_id = vtu_service.get_data_plan_price(session['provider'], plan)
                    result['price'] = price
                    result['variation_id'] = variation_id
                except Exception as e:
                    result['error'] = str(e)
            t = threading.Thread(target=fetch_price)
            t.start()
            t.join(timeout=30)  # 30 seconds max
            if t.is_alive():
                return "⚠️ Data plan lookup timed out. Please try again.", session, True
            if 'error' in result:
                return f"⚠️ Error fetching price: {result['error']}", session, True
            price, variation_id = result.get('price'), result.get('variation_id')
            if price is None or variation_id is None:
                return f"⚠️ Could not fetch price for {plan} on {session['provider']}. Please try again later.", session, True
            session['plan_price'] = price
            session['variation_id'] = variation_id
        except Exception as e:
            return f"⚠️ Error fetching price: {e}", session, True
        session['step'] = 3
        return f"Enter Recipient Phone Number for {session['provider']} {plan} Data:\n(Price: NGN {session['plan_price']})", session, False

    if step == 3:
        session['target'] = msg
        session['step'] = 4
        if session.get('service') == 'Data':
            # Use fetched plan price for data
            return f"You will be charged NGN {session.get('plan_price', 'N/A')} for {session.get('plan', '')} Data. Confirm to proceed (yes/no):", session, False
        else:
            return "Enter Amount (NGN):", session, False

    if step == 4:
        # Final confirmation and VTU API call
        provider = session.get('provider', 'N/A')
        service = session.get('service', 'N/A')
        target = session.get('target', 'N/A')
        try:
            from services.vtu_service import VTUApiClient
            import uuid
            from modules import notifications
            import config
            client = VTUApiClient()
            request_id = f"req_{uuid.uuid4().hex[:12]}"
            if service == 'Airtime':
                provider_map = {'MTN': 'mtn', 'Airtel': 'airtel', 'Glo': 'glo', '9mobile': '9mobile'}
                service_id = provider_map.get(provider.lower().capitalize(), provider.lower())
                amount = int(session.get('plan_price') or session.get('amount') or 100)
                if not amount:
                    return "❌ Amount required for airtime.", session, True
                resp = client.purchase_airtime(request_id, target, service_id, amount)
                msg = f"✅ Airtime purchase initiated for {target} on {provider}.\nStatus: {resp.get('message', 'Unknown')}"
                admin_msg = f"📱 *VTU Airtime Purchase*\nUser: {user.phone}\nProvider: {provider}\nAmount: NGN {amount}\nRecipient: {target}\nStatus: {resp.get('message', 'Unknown')}"
                notifications.send_push(type('Admin', (), {'phone': config.OWNER_PHONE.split(',')[0]}), admin_msg)
                return msg, session, True
            elif service == 'Data':
                provider_map = {'MTN': 'mtn', 'Airtel': 'airtel', 'Glo': 'glo', '9mobile': '9mobile'}
                service_id = provider_map.get(provider.lower().capitalize(), provider.lower())
                variation_id = session.get('variation_id')
                if not variation_id:
                    return "❌ Data plan variation ID missing.", session, True
                resp = client.purchase_data(request_id, target, service_id, variation_id)
                msg = f"✅ Data purchase initiated for {target} on {provider}.\nStatus: {resp.get('message', 'Unknown')}"
                admin_msg = f"📶 *VTU Data Purchase*\nUser: {user.phone}\nProvider: {provider}\nPlan: {session.get('plan', 'N/A')}\nAmount: NGN {session.get('plan_price', 'N/A')}\nRecipient: {target}\nStatus: {resp.get('message', 'Unknown')}"
                notifications.send_push(type('Admin', (), {'phone': config.OWNER_PHONE.split(',')[0]}), admin_msg)
                return msg, session, True
            else:
                return f"✅ Processing {service} for {target} on {provider}...", session, True
        except Exception as e:
            return f"❌ VTU API error: {e}", session, True