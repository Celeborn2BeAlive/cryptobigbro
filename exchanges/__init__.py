from .bitmex_exchange import BitmexExchange
from .binance_exchange import BinanceExchange
from .coinbasepro_exchange import CoinbaseProExchange

def make_bitmex_exchange():
    return BitmexExchange()

def make_binance_exchange():
    return BinanceExchange()

def make_coinbasepro_exchange(api_key=None):
    return CoinbaseProExchange(api_key)