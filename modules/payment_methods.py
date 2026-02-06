import logging
import re
import time
from datetime import datetime
import requests
from services.vtu_service import VTUApiClient

# --- VTU.ng API Betting Account Funding Wrapper (Production Ready) ---
def is_valid_betting_service_id(service_id):
    return service_id in {
        "1xBet", "BangBet", "Bet9ja", "BetKing", "BetLand", "BetLion", "BetWay", "CloudBet",
        "LiveScoreBet", "MerryBet", "NaijaBet", "NairaBet", "SupaBet"
    }

def is_valid_betting_amount(amount):
    try:
        amt = int(amount)
        return 100 <= amt <= 100000
    except Exception:
        return False

def fund_betting_account(user_id, customer_id, service_id, amount, max_retries=3):
    """
    Fund a betting account for a user using VTU.ng API (production ready).
    Args:
        user_id: Your internal user/customer ID (for logging/tracking)
        customer_id: Betting account ID
        service_id: Betting provider
        amount: Amount in NGN
        max_retries: Number of retries for transient errors
    Returns:
        dict: API response (success or error)
    """
    if not customer_id or not str(customer_id).isalnum():
        logger.warning(f"Invalid customer_id: {customer_id} (user_id={user_id})")
        return {"code": "invalid_customer_id", "message": "Invalid betting account ID."}
    if not is_valid_betting_service_id(service_id):
        logger.warning(f"Invalid service_id: {service_id} (user_id={user_id})")
        return {"code": "invalid_service_id", "message": "Invalid betting provider."}
    if not is_valid_betting_amount(amount):
        logger.warning(f"Invalid amount: {amount} (user_id={user_id})")
        return {"code": "invalid_amount", "message": "Amount must be between 100 and 100000 NGN."}

    vtu_client = VTUApiClient()
    request_id = f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
    attempt = 0
    while attempt < max_retries:
        try:
            response = vtu_client.fund_betting_account(request_id, str(customer_id), service_id, int(amount))
            logger.info(f"Betting funding: user_id={user_id}, customer_id={customer_id}, service_id={service_id}, amount={amount}, response={response}")
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
            attempt += 1
        except Exception as e:
            logger.error(f"Betting funding failed: user_id={user_id}, customer_id={customer_id}, service_id={service_id}, amount={amount}, error={e}")
            return {"code": "error", "message": str(e)}
    return {"code": "network_error", "message": "Failed to connect to VTU service after multiple attempts."}
# --- VTU.ng API ePINs Wrapper (Production Ready) ---
def is_valid_epins_service_id(service_id):
    return service_id in {"mtn", "airtel", "glo", "9mobile"}

def is_valid_epins_value(value):
    return str(value) in {"100", "200", "500"}

def is_valid_epins_quantity(quantity):
    try:
        qty = int(quantity)
        return 1 <= qty <= 40
    except Exception:
        return False

def buy_epins(user_id, service_id, value, quantity, max_retries=3):
    """
    Buy ePINs for a user using VTU.ng API (production ready).
    Args:
        user_id: Your internal user/customer ID (for logging/tracking)
        service_id: Network provider (mtn, airtel, glo, 9mobile)
        value: PIN denomination (100, 200, 500)
        quantity: Number of PINs (1-40)
        max_retries: Number of retries for transient errors
    Returns:
        dict: API response (success or error)
    """
    if not is_valid_epins_service_id(service_id):
        logger.warning(f"Invalid service_id: {service_id} (user_id={user_id})")
        return {"code": "invalid_service_id", "message": "Invalid ePINs provider."}
    if not is_valid_epins_value(value):
        logger.warning(f"Invalid value: {value} (user_id={user_id})")
        return {"code": "invalid_value", "message": "Invalid ePIN denomination. Must be 100, 200, or 500."}
    if not is_valid_epins_quantity(quantity):
        logger.warning(f"Invalid quantity: {quantity} (user_id={user_id})")
        return {"code": "invalid_quantity", "message": "Quantity must be between 1 and 40."}

    vtu_client = VTUApiClient()
    request_id = f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
    attempt = 0
    while attempt < max_retries:
        try:
            response = vtu_client.purchase_epins(request_id, service_id, int(value), int(quantity))
            logger.info(f"ePINs purchase: user_id={user_id}, service_id={service_id}, value={value}, quantity={quantity}, response={response}")
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
            attempt += 1
        except Exception as e:
            logger.error(f"ePINs purchase failed: user_id={user_id}, service_id={service_id}, value={value}, quantity={quantity}, error={e}")
            return {"code": "error", "message": str(e)}
    return {"code": "network_error", "message": "Failed to connect to VTU service after multiple attempts."}
# --- VTU.ng API TV Subscription Wrapper (Production Ready) ---
def is_valid_tv_service_id(service_id):
    return service_id in {"dstv", "gotv", "startimes", "showmax"}

def is_valid_tv_variation_id(variation_id):
    return str(variation_id).isdigit() and int(variation_id) > 0

def buy_tv_subscription(user_id, customer_id, service_id, variation_id, subscription_type=None, amount=None, max_retries=3):
    """
    Buy TV subscription for a user using VTU.ng API (production ready).
    Args:
        user_id: Your internal user/customer ID (for logging/tracking)
        customer_id: Smartcard or IUC number
        service_id: TV provider (dstv, gotv, startimes, showmax)
        variation_id: Package/bouquet variation ID (from VTU API)
        subscription_type: 'change' or 'renew' (optional)
        amount: Amount in NGN (optional, for renewals)
        max_retries: Number of retries for transient errors
    Returns:
        dict: API response (success or error)
    """
    if not customer_id or not str(customer_id).isdigit():
        logger.warning(f"Invalid customer_id: {customer_id} (user_id={user_id})")
        return {"code": "invalid_customer_id", "message": "Invalid smartcard/IUC number."}
    if not is_valid_tv_service_id(service_id):
        logger.warning(f"Invalid service_id: {service_id} (user_id={user_id})")
        return {"code": "invalid_service_id", "message": "Invalid TV provider."}
    if not is_valid_tv_variation_id(variation_id):
        logger.warning(f"Invalid variation_id: {variation_id} (user_id={user_id})")
        return {"code": "invalid_variation_id", "message": "Invalid TV package variation ID."}
    if subscription_type and subscription_type not in {"change", "renew"}:
        logger.warning(f"Invalid subscription_type: {subscription_type} (user_id={user_id})")
        return {"code": "invalid_subscription_type", "message": "Invalid subscription type. Must be 'change' or 'renew'."}
    if amount is not None:
        try:
            amt = int(amount)
            if amt < 1 or amt > 100000:
                raise ValueError
        except Exception:
            logger.warning(f"Invalid amount: {amount} (user_id={user_id})")
            return {"code": "invalid_amount", "message": "Invalid amount for TV subscription."}

    vtu_client = VTUApiClient()
    request_id = f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
    attempt = 0
    while attempt < max_retries:
        try:
            response = vtu_client.purchase_tv_subscription(
                request_id, str(customer_id), service_id, str(variation_id), subscription_type, amount
            )
            logger.info(f"TV subscription: user_id={user_id}, customer_id={customer_id}, service_id={service_id}, variation_id={variation_id}, subscription_type={subscription_type}, amount={amount}, response={response}")
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
            attempt += 1
        except Exception as e:
            logger.error(f"TV subscription failed: user_id={user_id}, customer_id={customer_id}, service_id={service_id}, variation_id={variation_id}, subscription_type={subscription_type}, amount={amount}, error={e}")
            return {"code": "error", "message": str(e)}
    return {"code": "network_error", "message": "Failed to connect to VTU service after multiple attempts."}
# --- VTU.ng API Electricity Wrapper (Production Ready) ---
def is_valid_electricity_service_id(service_id):
    return service_id in {
        "ikeja-electric", "eko-electric", "kano-electric", "portharcourt-electric", "jos-electric",
        "ibadan-electric", "kaduna-electric", "abuja-electric", "enugu-electric", "benin-electric",
        "aba-electric", "yola-electric"
    }

def is_valid_meter_type(variation_id):
    return variation_id in {"prepaid", "postpaid"}

def is_valid_electricity_amount(amount):
    try:
        amt = int(amount)
        return amt >= 100 and amt <= 100000
    except Exception:
        return False

def buy_electricity(user_id, customer_id, service_id, variation_id, amount, max_retries=3):
    """
    Buy electricity for a user using VTU.ng API (production ready).
    Args:
        user_id: Your internal user/customer ID (for logging/tracking)
        customer_id: Meter or account number
        service_id: Electricity provider
        variation_id: Meter type ('prepaid' or 'postpaid')
        amount: Amount in NGN
        max_retries: Number of retries for transient errors
    Returns:
        dict: API response (success or error)
    """
    if not customer_id or not str(customer_id).isdigit():
        logger.warning(f"Invalid customer_id: {customer_id} (user_id={user_id})")
        return {"code": "invalid_customer_id", "message": "Invalid meter/account number."}
    if not is_valid_electricity_service_id(service_id):
        logger.warning(f"Invalid service_id: {service_id} (user_id={user_id})")
        return {"code": "invalid_service_id", "message": "Invalid electricity provider."}
    if not is_valid_meter_type(variation_id):
        logger.warning(f"Invalid meter type: {variation_id} (user_id={user_id})")
        return {"code": "invalid_meter_type", "message": "Invalid meter type. Must be 'prepaid' or 'postpaid'."}
    if not is_valid_electricity_amount(amount):
        logger.warning(f"Invalid amount: {amount} (user_id={user_id})")
        return {"code": "invalid_amount", "message": "Amount must be between 100 and 100000 NGN."}

    vtu_client = VTUApiClient()
    request_id = f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
    attempt = 0
    while attempt < max_retries:
        try:
            response = vtu_client.purchase_electricity(request_id, str(customer_id), service_id, variation_id, int(amount))
            logger.info(f"Electricity purchase: user_id={user_id}, customer_id={customer_id}, service_id={service_id}, variation_id={variation_id}, amount={amount}, response={response}")
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
            attempt += 1
        except Exception as e:
            logger.error(f"Electricity purchase failed: user_id={user_id}, customer_id={customer_id}, service_id={service_id}, variation_id={variation_id}, amount={amount}, error={e}")
            return {"code": "error", "message": str(e)}
    return {"code": "network_error", "message": "Failed to connect to VTU service after multiple attempts."}
# --- VTU.ng API Data Wrapper (Production Ready) ---
def is_valid_variation_id(variation_id):
    return str(variation_id).isdigit() and int(variation_id) > 0

def buy_data(user_id, phone, service_id, variation_id, max_retries=3):
    """
    Buy data for a user using VTU.ng API (production ready).
    Args:
        user_id: Your internal user/customer ID (for logging/tracking)
        phone: Phone number to recharge
        service_id: Network provider (e.g., 'mtn', 'airtel', 'glo', '9mobile', 'smile')
        variation_id: Data plan variation ID (from VTU API)
        max_retries: Number of retries for transient errors
    Returns:
        dict: API response (success or error)
    """
    if not is_valid_phone(phone):
        logger.warning(f"Invalid phone: {phone} (user_id={user_id})")
        return {"code": "invalid_phone", "message": "Invalid phone number format."}
    if service_id not in {"mtn", "airtel", "glo", "9mobile", "smile"}:
        logger.warning(f"Invalid service_id: {service_id} (user_id={user_id})")
        return {"code": "invalid_service_id", "message": "Invalid service provider."}
    if not is_valid_variation_id(variation_id):
        logger.warning(f"Invalid variation_id: {variation_id} (user_id={user_id})")
        return {"code": "invalid_variation_id", "message": "Invalid data plan variation ID."}

    vtu_client = VTUApiClient()
    request_id = f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
    attempt = 0
    while attempt < max_retries:
        try:
            response = vtu_client.purchase_data(request_id, phone, service_id, str(variation_id))
            logger.info(f"Data purchase: user_id={user_id}, phone={phone}, service_id={service_id}, variation_id={variation_id}, response={response}")
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
            attempt += 1
        except Exception as e:
            logger.error(f"Data purchase failed: user_id={user_id}, phone={phone}, service_id={service_id}, variation_id={variation_id}, error={e}")
            return {"code": "error", "message": str(e)}
    return {"code": "network_error", "message": "Failed to connect to VTU service after multiple attempts."}
# payment_methods.py
# Store all off-chain payment method details here for easy management.

PAYMENT_METHODS = {
    "paypal": {
        "label": "PayPal",
        "instructions": "Send payment to the following PayPal email:",
        "details": "your-paypal-email@example.com"
    },
    "cashapp": {
        "label": "CashApp",
        "instructions": "Send payment to the following CashApp username:",
        "details": "$YourCashAppTag"
    },
    "venmo": {
        "label": "Venmo",
        "instructions": "Send payment to the following Venmo username:",
        "details": "@YourVenmoUsername"
    },
    "zelle": {
        "label": "Zelle",
        "instructions": "Send payment to the following Zelle email or phone:",
        "details": "your-zelle-email@example.com"
    },
    "bank": {
        "label": "Bank Transfer",
        "instructions": "Send a bank transfer using the following details:",
        "details": "Bank Name: Your Bank\nAccount Number: 123456789\nRouting Number: 987654321\nAccount Name: Your Name"
    }
}



# --- VTU.ng API Airtime Wrapper (Production Ready) ---

# Setup logger (shared for all VTU services)
logger = logging.getLogger("vtu_airtime")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("logs/vtu_airtime.log")
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

def is_valid_phone(phone):
    # Accepts 11-16 digits, with or without +234
    return bool(re.match(r"^(\+234|0)?[789][01]\d{8,13}$", phone))

def is_valid_service_id(service_id):
    return service_id in {"mtn", "airtel", "glo", "9mobile"}

def is_valid_amount(amount):
    try:
        amt = int(amount)
        return amt >= 10 and amt <= 50000
    except Exception:
        return False

def buy_airtime(user_id, phone, service_id, amount, max_retries=3):
    """
    Buy airtime for a user using VTU.ng API (production ready).
    Args:
        user_id: Your internal user/customer ID (for logging/tracking)
        phone: Phone number to recharge
        service_id: Network provider (e.g., 'mtn', 'airtel', 'glo', '9mobile')
        amount: Amount in NGN
        max_retries: Number of retries for transient errors
    Returns:
        dict: API response (success or error)
    """
    # Input validation
    if not is_valid_phone(phone):
        logger.warning(f"Invalid phone: {phone} (user_id={user_id})")
        return {"code": "invalid_phone", "message": "Invalid phone number format."}
    if not is_valid_service_id(service_id):
        logger.warning(f"Invalid service_id: {service_id} (user_id={user_id})")
        return {"code": "invalid_service_id", "message": "Invalid service provider."}
    if not is_valid_amount(amount):
        logger.warning(f"Invalid amount: {amount} (user_id={user_id})")
        return {"code": "invalid_amount", "message": "Amount must be between 10 and 50000 NGN."}

    vtu_client = VTUApiClient()
    request_id = f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
    attempt = 0
    while attempt < max_retries:
        try:
            response = vtu_client.purchase_airtime(request_id, phone, service_id, int(amount))
            logger.info(f"Airtime purchase: user_id={user_id}, phone={phone}, service_id={service_id}, amount={amount}, response={response}")
            # TODO: Save transaction to DB here if needed
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
            attempt += 1
        except Exception as e:
            logger.error(f"Airtime purchase failed: user_id={user_id}, phone={phone}, service_id={service_id}, amount={amount}, error={e}")
            return {"code": "error", "message": str(e)}
    return {"code": "network_error", "message": "Failed to connect to VTU service after multiple attempts."}
