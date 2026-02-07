from dotenv import load_dotenv
load_dotenv()
# VTU.ng API Integration
import os
import requests
import hmac
import hashlib
import json

AUTH_URL = "https://vtu.ng/wp-json/jwt-auth/v1/token"
API_URL = "https://vtu.ng/wp-json/api/v2/"

class VTUApiClient:
    def __init__(self, username=None, password=None, user_pin=None):
        self.username = username or os.getenv("VTU_USERNAME", "your_vtu_username")
        self.password = password or os.getenv("VTU_PASSWORD", "your_vtu_password")
        self.user_pin = user_pin or os.getenv("VTU_USER_PIN", "your_user_pin")
        self.token = None

    def get_access_token(self):
        payload = {"username": self.username, "password": self.password}
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(AUTH_URL, json=payload, headers=headers)
            print(f"[DEBUG] Auth POST {AUTH_URL} status={response.status_code}")
            print(f"[DEBUG] Auth response: {response.text}")
            response.raise_for_status()
            data = response.json()
            if "token" in data:
                self.token = data["token"]
                return self.token
            raise Exception(data.get("message", "Authentication failed"))
        except Exception as e:
            print(f"[DEBUG] Auth exception: {e}")
            raise

    def get_headers(self):
        if not self.token:
            self.get_access_token()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def check_balance(self):
        response = requests.get(f"{API_URL}balance", headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def purchase_airtime(self, request_id, phone, service_id, amount):
        payload = {
            "request_id": request_id,
            "phone": phone,
            "service_id": service_id,
            "amount": amount
        }
        response = requests.post(f"{API_URL}airtime", json=payload, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def get_data_variations(self, service_id=None):
        # Corrected endpoint and parameter for VTU.ng API v2
        url = f"{API_URL}variations/data"
        if service_id:
            url += f"?service_id={service_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def purchase_data(self, request_id, phone, service_id, variation_id):
        payload = {
            "request_id": request_id,
            "phone": phone,
            "service_id": service_id,
            "variation_id": variation_id
        }
        response = requests.post(f"{API_URL}data", json=payload, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def verify_customer(self, service_id, customer_id, variation_id=None):
        payload = {"customer_id": customer_id, "service_id": service_id}
        if variation_id:
            payload["variation_id"] = variation_id
        response = requests.post(f"{API_URL}verify-customer", json=payload, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def purchase_electricity(self, request_id, customer_id, service_id, variation_id, amount):
        payload = {
            "request_id": request_id,
            "customer_id": customer_id,
            "service_id": service_id,
            "variation_id": variation_id,
            "amount": amount
        }
        response = requests.post(f"{API_URL}electricity", json=payload, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def fund_betting_account(self, request_id, customer_id, service_id, amount):
        payload = {
            "request_id": request_id,
            "customer_id": customer_id,
            "service_id": service_id,
            "amount": amount
        }
        response = requests.post(f"{API_URL}betting", json=payload, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def get_tv_variations(self, service_id=None):
        url = f"{API_URL}variations/tv"
        if service_id:
            url += f"?service_id={service_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def purchase_tv_subscription(self, request_id, customer_id, service_id, variation_id, subscription_type=None, amount=None):
        payload = {
            "request_id": request_id,
            "customer_id": customer_id,
            "service_id": service_id,
            "variation_id": variation_id
        }
        if subscription_type:
            payload["subscription_type"] = subscription_type
        if amount:
            payload["amount"] = amount
        response = requests.post(f"{API_URL}tv", json=payload, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def purchase_epins(self, request_id, service_id, value, quantity):
        payload = {
            "request_id": request_id,
            "service_id": service_id,
            "value": value,
            "quantity": quantity
        }
        response = requests.post(f"{API_URL}epins", json=payload, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def requery_order(self, request_id):
        payload = {"request_id": request_id}
        response = requests.post(f"{API_URL}requery", json=payload, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def verify_webhook(self, payload, signature):
        computed_signature = hmac.new(
            self.user_pin.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed_signature, signature)

    def get_data_plan_price(self, provider, plan):
        """
        Fetch the live price and variation_id for a data plan from vtu.ng for the given provider and plan.
        provider: 'MTN', 'Airtel', 'Glo', '9mobile'
        plan: e.g. '500MB', '1GB', '2GB', '5GB'
        Returns: (price as int, variation_id as str) or (None, None) if not found
        """
        provider_service_ids = {
            'MTN': 'mtn',
            'Airtel': 'airtel',
            'Glo': 'glo',
            '9mobile': '9mobile',
        }
        service_id = provider_service_ids.get(provider)
        if not service_id:
            return None, None
        try:
            client = VTUApiClient()
            variations = client.get_data_variations(service_id)
            for v in variations.get('data', []):
                if plan.lower() in v.get('data_plan', '').lower() and v.get('availability', '').lower() == 'available':
                    price = int(float(v.get('price', 0)))
                    variation_id = str(v.get('variation_id'))
                    return price, variation_id
        except Exception as e:
            print(f"[VTU] Error fetching data plan price: {e}")
            return None, None
        return None, None

def get_data_plan_price(provider, plan):
    """
    Fetch the live price and variation_id for a data plan from vtu.ng for the given provider and plan.
    Returns: (price as int, variation_id as str) or (None, None) if not found
    """
    provider_service_ids = {
        'MTN': 'mtn',
        'Airtel': 'airtel',
        'Glo': 'glo',
        '9mobile': '9mobile',
    }
    service_id = provider_service_ids.get(provider)
    if not service_id:
        return None, None
    try:
        client = VTUApiClient()
        variations = client.get_data_variations(service_id)
        for v in variations.get('data', []):
            if plan.lower() in v.get('data_plan', '').lower() and v.get('availability', '').lower() == 'available':
                price = int(float(v.get('price', 0)))
                variation_id = str(v.get('variation_id'))
                return price, variation_id
    except Exception as e:
        print(f"[VTU] Error fetching data plan price: {e}")
        return None, None
    return None, None

# Example usage:
# vtu_client = VTUApiClient()
# balance = vtu_client.check_balance()
# print(balance)
# vtu_service.py
"""
Production-grade VTU (Virtual Top-Up) Service Module Scaffold
- Supports Airtime, Data, and Utility Top-Ups
- Pluggable for any VTU API provider
- Handles user balance deduction, transaction logging, and provider API integration
"""
import requests
import os
from database import Transaction, db, Wallet

