from .bitmex_exchange import BitmexExchange
from .binance_exchange import BinanceExchange
from .coinbasepro_exchange import CoinbaseProExchange

def make_bitmex_exchange():
    return BitmexExchange()

def make_binance_exchange():
    return BinanceExchange()

def make_coinbasepro_exchange(api_key=None):
    return CoinbaseProExchange(api_key)

def make_backtest_exchange(config_dict):
    return None

def make_exchange(config_dict):
    if config_dict["name"] == "coinbasepro":
        return make_coinbasepro_exchange(config_dict) if "apiKey" in config_dict else make_coinbasepro_exchange()
    elif config_dict["name"] == "binance":
        return make_binance_exchange()
    elif config_dict["name"] == "bitmex":
        return make_bitmex_exchange()
    elif config_dict["name"] == "backtest":
        return make_backtest_exchange(config_dict)