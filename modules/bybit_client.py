def print_all_deposit_addresses():
    """
    Utility: Print all available deposit addresses for SUPPORTED_COINS and SUPPORTED_CHAINS.
    Helps debug which assets/chains are active for this API key/account.
    """
    for coin in SUPPORTED_COINS:
        chains = SUPPORTED_CHAINS.get(coin, [])
        for chain in chains:
            address = get_deposit_address(coin, chain)
            if address:
                print(f"[OK] {coin} on {chain}: {address}")
            else:
                print(f"[NO ADDRESS] {coin} on {chain}")
from pybit.unified_trading import HTTP
import config

# Production-ready: Supported coins and chains
SUPPORTED_COINS = [
    "USDT", "BTC", "ETH", "SOL", "BNB", "TRX"
]
SUPPORTED_CHAINS = {
    "USDT": ["TRC20", "ERC20", "BEP20", "SOL"],
    "BTC": ["BTC", "BNB"],
    "ETH": ["ERC20"],
    "SOL": ["SOL"],
    "BNB": ["BEP20", "BNB"],
    "TRX": ["TRC20"]
}

def get_client():
    """
    Returns a Bybit HTTP client using credentials from config.
    """
    return HTTP(
        testnet=config.USE_TESTNET,
        api_key=config.BYBIT_API_KEY,
        api_secret=config.BYBIT_API_SECRET
    )

def get_deposit_address(coin="USDT", chain="TRC20"):
    """
    Returns the deposit address for a given coin and chain.
    Checks static_deposit_addresses first, then falls back to Bybit API.
    Returns None if not available or on error.
    """
    coin = coin.upper()
    chain = chain.upper()

    if coin not in SUPPORTED_COINS:
        print(f"[ERROR] Coin '{coin}' is not supported. Supported: {SUPPORTED_COINS}")
        return None

    if chain not in SUPPORTED_CHAINS.get(coin, []):
        print(f"[ERROR] Chain '{chain}' is not supported for {coin}. Supported: {SUPPORTED_CHAINS.get(coin, [])}")
        return None

    # Try static deposit addresses first
    try:
        from static_deposit_addresses import STATIC_DEPOSIT_ADDRESSES
        static_addr = STATIC_DEPOSIT_ADDRESSES.get(chain, {}).get(coin)
        if static_addr:
            return static_addr
    except Exception as e:
        print(f"[Static Address Error] {e}")

    # Fallback to Bybit API
    try:
        session = get_client()
        response = session.get_master_deposit_address(coin=coin, chainType=chain)
        print(f"Bybit Response: {response}")

        if response.get('retCode') == 0:
            chain_list = response['result'].get('chains', [])
            if not chain_list:
                print(f"[INFO] No deposit address exists yet for {coin} on {chain}.")
                return None
            # Find the correct chain address
            for c in chain_list:
                if c.get('chainType', '').upper() == chain:
                    return c.get('addressDeposit')
            # Fallback: return first address if specific chain not found
            return chain_list[0].get('addressDeposit')
        else:
            print(f"[Bybit Error] {response.get('retMsg')}")
            return None
    except Exception as e:
        print(f"[Code Error] {e}")
        return None