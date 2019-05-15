import cbpro
import pandas as pd
from datetime import datetime, timezone
from utils import timedelta, candle_list_to_dataframe, compute_end_timestamp
from .crypto_assets import CryptoAssetInfo, CryptoInstrumentPairInfo

# API used: https://github.com/danpaquin/coinbasepro-python

class CoinbaseProExchange:
    def __init__(self):
        self._client = cbpro.PublicClient()
    
    def name(self):
        return "coinbasepro"

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
            start=since.timestamp()
        )
        result = reversed(result) # Coinbase pro is sending candles from newest to oldest, we need to reverse that
        
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