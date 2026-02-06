import ccxt
import config

def get_exchange():
    # --- DEBUG SPY REMOVED (We know keys are present) ---

    try:
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
        exchange = exchange_class({
            'apiKey': config.API_KEY,
            'secret': config.API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap', # Try 'spot' first, if fails we try 'swap'
                'adjustForTimeDifference': True, # crucial for syncing timestamps
                'recvWindow': 10000, # gives more time for request to process
            }
        })
        
        # FORCE V5 API (Crucial for new Bybit accounts)
        if config.EXCHANGE_ID == 'bybit':
            exchange.options['defaultType'] = 'spot' 
            # Note: CCXT uses V5 by default now, but let's be sure
        
        return exchange
    except Exception as e:
        print(f"Error initializing exchange: {e}")
        return None

def get_price(symbol):
    exchange = get_exchange()
    ticker = exchange.fetch_ticker(symbol)
    return ticker['last']

def get_balance():
    exchange = get_exchange()
    # This is the line that fails if keys are missing
    balance = exchange.fetch_balance()
    total = balance['total']
    return {k: v for k, v in total.items() if v > 0}

def execute_trade(symbol, side, amount):
    exchange = get_exchange()
    order = exchange.create_order(symbol, 'market', side, amount)
    return order