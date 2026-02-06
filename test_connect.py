import requests
import socket

def check_connection():
    print("🕵️ DIAGNOSTIC TOOL")
    print("━━━━━━━━━━━━━━━━")
    
    # 1. CHECK IP (Are we actually on VPN?)
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text
        print(f"✅ Internet: CONNECTED")
        print(f"🌍 Current IP: {ip} (Check if this matches your VPN location)")
    except Exception as e:
        print(f"❌ Internet: FAILED ({e})")
        return

    # 2. CHECK DNS RESOLUTION (Can we find Bybit?)
    print("\n🔍 Checking DNS Resolution...")
    try:
        addr = socket.gethostbyname("api.bybit.com")
        print(f"✅ DNS Success: api.bybit.com = {addr}")
    except Exception as e:
        print(f"❌ DNS FAILED: Could not resolve address. ({e})")
        print("   -> Your ISP is blocking the name lookup.")

    # 3. CHECK HTTPS HANDSHAKE (Can we talk to Bybit?)
    print("\n🤝 Checking Bybit Connection...")
    try:
        r = requests.get("https://api.bybit.com/v5/market/time", timeout=10)
        print(f"✅ Bybit Status: {r.status_code} OK")
        print("   -> The connection is healthy!")
    except Exception as e:
        print(f"❌ Bybit FAILED: {e}")

if __name__ == "__main__":
    check_connection()