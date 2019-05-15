import pandas as pd
import requests
from datetime import datetime, timezone

from utils import timedelta, candle_list_to_dataframe

from .crypto_assets import CryptoAssetInfo, CryptoInstrumentInfo

def bitmex_request_get(endpoint, params=None):
        url = "https://www.bitmex.com/api/v1" + endpoint
        r = requests.get(url, params=params)
        # print(r.headers['x-ratelimit-limit'])
        # print(r.headers['x-ratelimit-remaining'])
        # print(r.headers['x-ratelimit-reset'])
        if r.status_code != 200:
            raise RuntimeError("Unable to reach {}.".format(url))
        return r.json()

class BitmexExchange:
    def __init__(self):
        self._limit = 750 # Max number of candles that bitmex is sending
        self._instrument_info = { _["symbol"]: _ for _ in bitmex_request_get("/instrument") }
    def name(self):
        return "bitmex"

    def get_utc_timestamp(self):
        j = bitmex_request_get("")
        return int(j["timestamp"] / 1000)
    
    def get_utc_time(self):
        return datetime.fromtimestamp(self.get_utc_timestamp(), timezone.utc)

    def fetch_ohlcv(self, timeframe, since, instrument):
        # adding one time interval because Bitmex api is returning us close times instead of open times
        closeDate = since + timedelta(timeframe)

        params = (
            ('binSize', timeframe),
            ('symbol', instrument),
            ('reverse', "false"),
            ('count', self._limit),
            ('startTime', str(closeDate))
        )

        try:
            result = bitmex_request_get("/trade/bucketed", params=params)
        except e:
            print(e)
            print("To many requests, try again later.")
            result = []

        for r in result:
            r['timestamp'] = datetime.strptime(r['timestamp'].split(".")[0] + " UTC", '%Y-%m-%dT%H:%M:%S %Z').replace(tzinfo=timezone.utc)

        candles = [candle for candle in result if candle["open"]] # Filter bad data

        # compute open and close times of each candle
        for candle in candles:
            candle["open_datetime_utc"] = candle['timestamp'] - timedelta(timeframe)
            candle["close_datetime_utc"] = candle['timestamp'] - timedelta('1s')
            candle["trade_count"] = candle["trades"]

        return candle_list_to_dataframe(candles)
    
    def get_assets(self):
        return []

    def get_timeframes(self):
        return [ "1d", "1h", "5m", "1m" ]
    
    def get_instruments(self):
        return self._instrument_info.keys()
    
    def get_instrument_info(self, instrument):
        info = self._instrument_info[instrument]
        return CryptoInstrumentInfo(info["symbol"], self.name(), "trading" if info["state"] == "Open" else "break", info)