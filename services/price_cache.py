import threading
import time
from services.coingecko_price import CoinGeckoPriceService

class PriceCache:
    def __init__(self, symbols, vs_currency='usdt', refresh_interval=60):
        self.symbols = symbols
        self.vs_currency = vs_currency
        self.refresh_interval = refresh_interval
        self.cache = {}
        self.last_update = 0
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

    def _update_loop(self):
        cg_service = CoinGeckoPriceService()
        while not self._stop_event.is_set():
            with self.lock:
                for symbol in self.symbols:
                    try:
                        price = cg_service.get_price(symbol, self.vs_currency)
                        if price:
                            self.cache[symbol.lower()] = price
                    except Exception as e:
                        print(f"[PriceCache] Error updating {symbol}: {e}")
                self.last_update = time.time()
            time.sleep(self.refresh_interval)

    def get(self, symbol):
        with self.lock:
            return self.cache.get(symbol.lower())

    def stop(self):
        self._stop_event.set()
        self.thread.join()
