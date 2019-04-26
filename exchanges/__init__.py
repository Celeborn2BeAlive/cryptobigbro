from .bitmex_exchange import BitmexExchange
from .binance_exchange import BinanceExchange

def make_bitmex_exchange():
    return BitmexExchange()

def make_binance_exchange():
    return BinanceExchange()