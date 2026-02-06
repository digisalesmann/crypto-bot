from pycoingecko import CoinGeckoAPI
from functools import lru_cache
import time

class CoinGeckoPriceService:
    def __init__(self):
        self.cg = CoinGeckoAPI()

    @lru_cache(maxsize=128)
    def get_price(self, symbol: str, vs_currency: str = 'usdt'):
        """
        Fetch the current price for a given symbol from CoinGecko.
        Uses LRU cache to avoid rate limits and improve performance.
        """
        try:
            # CoinGecko uses ids, not symbols. Map common symbols to ids.
            symbol_map = {
                'btc': 'bitcoin',
                'xbt': 'bitcoin',
                'eth': 'ethereum',
                'usdt': 'tether',
                'bnb': 'binancecoin',
                'sol': 'solana',
                # Add more as needed
            }
            # Try to map symbol, fallback to lower-case
            coin_id = symbol_map.get(symbol.lower(), symbol.lower())
            # Special handling for ETH (common issue)
            if symbol.lower() in ['eth', 'ethereum']:
                coin_id = 'ethereum'
            print(f"[DEBUG][CoinGecko] Fetching price for symbol: {symbol}, coin_id: {coin_id}, vs_currency: {vs_currency}")
            data = self.cg.get_price(ids=coin_id, vs_currencies=vs_currency)
            print(f"[DEBUG][CoinGecko] API response for {coin_id}: {data}")
            price = data.get(coin_id, {}).get(vs_currency)
            if price is None and vs_currency.lower() == 'usdt':
                print(f"[DEBUG][CoinGecko] No USDT price for {coin_id}, trying USD fallback...")
                data_usd = self.cg.get_price(ids=coin_id, vs_currencies='usd')
                print(f"[DEBUG][CoinGecko] USD API response for {coin_id}: {data_usd}")
                price_usd = data_usd.get(coin_id, {}).get('usd')
                return price_usd
            return price
        except Exception as e:
            print(f"[DEBUG][CoinGecko] API error for symbol: {symbol}, coin_id: {coin_id}, vs_currency: {vs_currency} | Error: {e}")
            return None

    def clear_cache(self):
        self.get_price.cache_clear()
