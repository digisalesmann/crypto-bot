from services.exchange import get_price
from database import Wallet, Transaction, db

# modules/swap.py
def handle_flow(user, msg, session):
    # Block if account is frozen
    if getattr(user, 'is_frozen', False):
        return ("❄️ Your account is currently frozen. Swaps are disabled. Contact support to unfreeze.", session, True)

    step = session.get('step')
    SUPPORTED_ASSETS = ['USDT', 'BTC', 'ETH', 'SOL', 'NGN']

    if step == 1:
        session['step'] = 2
        return "🔄 *Swap Assets*\nWhat are you swapping FROM? (USDT, BTC, ETH, SOL, NGN)", session, False

    if step == 2:
        asset_from = msg.upper().strip()
        if asset_from not in SUPPORTED_ASSETS:
            return (f"❌ Unsupported asset. Please choose from: {', '.join(SUPPORTED_ASSETS)}", session, False)
        session['from'] = asset_from
        session['step'] = 3
        return f"What are you swapping TO? (USDT, BTC, ETH, SOL, NGN)", session, False

    if step == 3:
        asset_to = msg.upper().strip()
        if asset_to not in SUPPORTED_ASSETS:
            return (f"❌ Unsupported asset. Please choose from: {', '.join(SUPPORTED_ASSETS)}", session, False)
        if asset_to == session['from']:
            return ("❌ You cannot swap to the same asset. Please choose a different asset.", session, False)
        session['to'] = asset_to
        session['step'] = 4
        return f"How much {session['from']} are you swapping?", session, False

    if step == 4:
        try:
            amt = float(msg)
            if amt <= 0:
                return ("❌ Amount must be positive.", session, False)
        except ValueError:
            return ("❌ Please enter a valid numeric amount.", session, False)
        from_asset = session['from']
        to_asset = session['to']
        # Use admin-set rates for NGN swaps, hybrid for other assets
        from config import ADMIN_SWAP_RATE_BUY, ADMIN_SWAP_RATE_SELL
        # CoinGecko fallback
        from services.coingecko_price import CoinGeckoPriceService
        cg = CoinGeckoPriceService()
        import time
        def get_price_with_fallback(from_asset, to_asset, timeout=60):
            import time
            start = time.time()
            pair = f"{to_asset}/USDT" if from_asset == 'USDT' else f"{from_asset}/USDT"
            try:
                return get_price(pair)
            except Exception:
                # Try CoinGecko
                base = to_asset if from_asset == 'USDT' else from_asset
                quote = 'usdt'
                price = None
                try:
                    price = cg.get_price(base, quote)
                except Exception as e:
                    print(f"[SWAP][CoinGecko] Error: {e}")
                if price is None and quote == 'usdt':
                    try:
                        price = cg.get_price(base, 'usd')
                    except Exception as e:
                        print(f"[SWAP][CoinGecko] USD fallback error: {e}")
                if price is None or price == {}:
                    elapsed = time.time() - start
                    if elapsed > timeout:
                        raise Exception('Rate fetch timed out')
                    raise Exception('No price found for this pair')
                return price

        try:
            if from_asset == 'NGN' and to_asset == 'USDT':
                rate = 1 / ADMIN_SWAP_RATE_BUY
                estimate = amt * rate
            elif from_asset == 'USDT' and to_asset == 'NGN':
                rate = ADMIN_SWAP_RATE_SELL
                estimate = amt * rate
            elif from_asset == 'NGN' and to_asset in SUPPORTED_ASSETS and to_asset != 'USDT':
                # NGN to other asset: NGN->USDT (admin rate), then USDT->asset (live rate)
                rate_ngn_usdt = 1 / ADMIN_SWAP_RATE_BUY
                amt_usdt = amt * rate_ngn_usdt
                rate_usdt_asset = get_price_with_fallback('USDT', to_asset)
                if rate_usdt_asset is None or rate_usdt_asset == 0:
                    return (f"❌ Unable to fetch rate for USDT to {to_asset}.", session, True)
                estimate = amt_usdt / rate_usdt_asset
                rate = rate_ngn_usdt / rate_usdt_asset
            elif to_asset == 'NGN' and from_asset in SUPPORTED_ASSETS and from_asset != 'USDT':
                asset_to_usdt = get_price_with_fallback(from_asset, 'USDT')
                rate = ADMIN_SWAP_RATE_SELL * asset_to_usdt
                estimate = amt * rate
            elif from_asset == 'USDT':
                rate = get_price_with_fallback('USDT', to_asset)
                estimate = amt / rate
            elif to_asset == 'USDT':
                rate = get_price_with_fallback(from_asset, 'USDT')
                estimate = amt * rate
            else:
                # For asset-to-asset swaps (e.g., BTC to ETH):
                rate_from = get_price_with_fallback(from_asset, 'USDT')
                rate_to = get_price_with_fallback(to_asset, 'USDT')
                usdt_amt = amt * rate_from
                estimate = usdt_amt / rate_to
                rate = rate_from / rate_to
        except Exception:
            return ("❌ Live rate unavailable for this pair.", session, True)
        session['est'] = estimate
        session['amt'] = amt
        session['rate'] = rate
        session['step'] = 5
        return f"📊 *Estimate*\n{amt} {from_asset} ≈ {estimate:.8f} {to_asset}\nRate: {rate:.4f}\n\nConfirm? (Yes/No)", session, False

    if step == 5:
        if msg.strip().lower() == 'yes':
            from_asset = session['from']
            to_asset = session['to']
            amt = session['amt']
            estimate = session['est']
            rate = session['rate']
            try:
                with db.atomic():
                    from_wallet = Wallet.get(Wallet.user == user, Wallet.currency == from_asset)
                    to_wallet, _ = Wallet.get_or_create(user=user, currency=to_asset, defaults={'balance': 0.0})
                    if from_wallet.balance < amt:
                        return (f"❌ Insufficient {from_asset} balance.", session, True)
                    from_wallet.balance -= amt
                    to_wallet.balance += estimate
                    from_wallet.save()
                    to_wallet.save()
                    Transaction.create(user=user, type='SWAP', currency=from_asset, amount=-amt, status='completed', tx_hash=f"SWAP->{to_asset}")
                    Transaction.create(user=user, type='SWAP', currency=to_asset, amount=estimate, status='completed', tx_hash=f"SWAP<-{from_asset}")
                # Notify Admin
                from modules import notifications
                import config
                admin_msg = f"🔄 *Swap Completed*\nUser: {user.phone}\n{amt} {from_asset} → {estimate:.2f} {to_asset}\nRate: {rate:.4f}"
                notifications.notify_admins(admin_msg)
                return (f"✅ Swap Complete!\n{amt} {from_asset} → {estimate:.2f} {to_asset}\nRate: {rate:.4f}", session, True)
            except Wallet.DoesNotExist:
                return (f"❌ You do not have a {from_asset} wallet.", session, True)
            except Exception as e:
                return (f"❌ Swap failed: {e}", session, True)
        elif msg.strip().lower() == 'no':
            return ("❌ Swap cancelled.", session, True)
        else:
            return ("❓ Please reply with 'Yes' to confirm or 'No' to cancel.", session, False)