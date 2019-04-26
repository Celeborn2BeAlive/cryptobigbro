import cbpro
import pandas as pd
from datetime import datetime, timezone
from utils import timedelta, candle_list_to_dataframe, compute_end_timestamp

# API used: https://github.com/danpaquin/coinbasepro-python

class CoinbaseProExchange:
    def __init__(self):
        self._client = cbpro.PublicClient()
    
    def utctimestamp(self):
        return int(self._client.get_time()['epoch'])
    
    def utcnow(self):
        return datetime.fromtimestamp(self.utctimestamp(), timezone.utc)

    def fetch_ohlcv(self, timeframe, since, instrument):
        # Binance include the current (and unfinished) bar in the fetched data, we need to compute endTime to remove it
        endTime = compute_end_timestamp(self.utcnow(), timeframe)
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