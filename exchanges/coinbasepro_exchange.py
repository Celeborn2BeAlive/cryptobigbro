import cbpro
import pandas as pd
from datetime import datetime, timezone
from utils import timedelta, candle_list_to_dataframe, compute_end_timestamp
from .crypto_assets import CryptoAssetInfo, CryptoInstrumentPairInfo

# API used: https://github.com/danpaquin/coinbasepro-python

def format_account_dict(a):
    for k in ['available', 'balance', 'hold']:
        a[k] = float(a[k])
    return a

class CoinbaseProExchange:
    def __init__(self, api_key=None):
        self._client = cbpro.PublicClient()
        if api_key:
            self._private_client = cbpro.AuthenticatedClient(api_key["apiKey"], api_key["apiSecret"], api_key["passPhrase"])
            accounts = self._private_client.get_accounts()
            if "message" in accounts:
                raise RuntimeError(accounts["message"])
        else:
            self._private_client = False
    
    def name(self):
        return "coinbasepro"

    def get_accounts(self):
        assert(self.is_authenticated())
        accounts = self._private_client.get_accounts()
        for a in accounts:
            a = format_account_dict(a)
        return accounts

    def get_account(self, account_id):
        assert(self.is_authenticated())
        account = self._private_client.get_account(account_id)
        return format_account_dict(account)

    def get_account_history(self, account_id, before=None):
        assert(self.is_authenticated())
        result = self._private_client.get_account_history(account_id, before=before) if before != None else self._private_client.get_account_history(account_id)
        return [ e for e in result if type(e) is dict ]

    def get_account_transfers(self, account_id, before=None):
        assert(self.is_authenticated())
        result = self._private_client.get_account_transfers(account_id, before=before) if before != None else self._private_client.get_account_transfers(account_id)
        return [ e for e in result if type(e) is dict ]

    def is_authenticated(self):
        return self._private_client != None

    def get_utc_timestamp(self):
        return int(self._client.get_time()['epoch'])
    
    def get_utc_time(self):
        return datetime.fromtimestamp(self.get_utc_timestamp(), timezone.utc)

    def fetch_ohlcv(self, timeframe, since, instrument):
        # Binance include the current (and unfinished) bar in the fetched data, we need to compute endTime to remove it
        endTime = compute_end_timestamp(self.get_utc_time(), timeframe)
        td = timedelta(timeframe)
        td_1s = timedelta('1s')
        result = self._client.get_product_historic_rates(
            instrument,
            granularity=int(td.total_seconds()),
            start=since.strftime("%Y-%m-%dT%H:%M")
        )
        try:
            result = reversed(result) # Coinbase pro is sending candles from newest to oldest, we need to reverse that
        except:
            print(result)
            print(since)
            print(since.timestamp())
            raise

        candles = [
            {
                "open_datetime_utc": datetime.fromtimestamp(int(data[0]), timezone.utc),
                "close_datetime_utc": datetime.fromtimestamp(int(data[0]), timezone.utc) + td - td_1s,
                "open": data[3],
                "high":data[2],
                "low":data[1],
                "close":data[4],
                "volume": data[5]
            } for data in result
        ]

        # We need to manually filter candles because Coinsebase Pro API might give us candles before our startDate and after our endDate
        candles = [ c for c in candles if since <= c['open_datetime_utc'] < endTime ]

        return candle_list_to_dataframe(candles)
    
    def get_timeframes(self):
        return [ "1d", "6h", "1h", "15m", "5m", "1m" ]
    
    def get_instruments(self):
        return [ _["id"] for _ in self._client.get_products() ]
    
    def get_assets(self):
        return [ _["id"] for _ in self._client.get_currencies() ]

    def get_instrument_info(self, instrument):
        products = self._client.get_products()
        for p in products:
            if p["id"] == instrument:
                return CryptoInstrumentPairInfo(p["id"], self.name(), p["base_currency"], p["quote_currency"], "trading" if p["status"] == "online" else "break", p)
        return None
    
    def get_asset_info(self, asset):
        currencies = self._client.get_currencies()
        for c in currencies:
            if c["id"] == asset:
                min_size = c["max_precision"]
                frac = min_size.split(".")[1]
                precision = 0
                while frac[precision] == "0":
                    precision += 1
                return CryptoAssetInfo(c["id"], precision + 1, c)
        return None
    
    def get_tickers(self):
        products = self._client.get_products()
        tickers = [
            self._client.get_product_ticker(p["id"]) for p in products if p["status"] == "online"
        ]
        for t in tickers:
            t["time"] = datetime.strptime(t['time'].split(".")[0] + " UTC", '%Y-%m-%dT%H:%M:%S %Z').replace(tzinfo=timezone.utc)
        return tickers
    
    def get_price(self, base, quote):
        return float(self._client.get_product_ticker(base + '-' + quote)['price'])
    
    def get_instrument_name(self, base, quote):
        return base + '-' + quote
    
    def get_order_book(self, instrument, level=1):
        return self._client.get_product_order_book(instrument, level=level)
    
    def clamp_to_min_max(self, instrument, size):
        products = [ p for p in self._client.get_products() if p["id"] == instrument ]
        min_size = float(products[0]["base_min_size"])
        max_size = float(products[0]["base_max_size"])
        return min(max(size, min_size), max_size)
    
    def place_buy_order(self, instrument, price, size, post_only, time_in_force, cancel_after):
        return self._private_client.place_order(product_id=instrument, side='buy', order_type='limit', price=price, size=size, 
            post_only=post_only, time_in_force=time_in_force, cancel_after=cancel_after)

    def get_order(self, id):
        return self._private_client.get_order(id)

    def cancel_order(self, id):
        return self._private_client.cancel_order(id)