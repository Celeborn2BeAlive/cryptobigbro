import bitmex
import bravado
import pandas as pd
import requests
from datetime import datetime, timezone

from utils import timedelta, candle_list_to_dataframe

# API used: https://github.com/BitMEX/api-connectors/tree/master/official-http/python-swaggerpy

class BitmexExchange:
    def __init__(self):
        self._client = bitmex.bitmex(test=False)
        self._limit = 750 # Max number of candles that bitmex is sending

        # Todo: replace usage of bitmex bravado API with simple requests:
        # d = datetime(year=2017, month=1, day=2, hour=0, minute=6, tzinfo=timezone.utc)

        # params = (
        #     ('binSize', '1m'),
        #     ('symbol', 'XBTUSD'),
        #     ('count', 750),
        #     ('startTime', str(d))
        # )

        # r = requests.get("https://www.bitmex.com/api/v1/trade/bucketed", params=params)
        # if r.status_code != 200:
        #     raise RuntimeError("Unable to reach https://www.bitmex.com/api/v1/trade/bucketed.")
        # j = r.json()
        # print(j[0])

    def get_utc_timestamp(self):
        r = requests.get("https://www.bitmex.com/api/v1")
        if r.status_code != 200:
            raise RuntimeError("Unable to reach https://www.bitmex.com/api/v1.")
        # print(r.headers['x-ratelimit-limit'])
        # print(r.headers['x-ratelimit-remaining'])
        # print(r.headers['x-ratelimit-reset'])
        j = r.json()
        return int(j["timestamp"] / 1000)
    
    def get_utc_time(self):
        return datetime.fromtimestamp(self.get_utc_timestamp(), timezone.utc)

    def fetch_ohlcv(self, timeframe, since, instrument):
        # adding one time interval because Bitmex api is returning us close times instead of open times
        closeDate = since + timedelta(timeframe)
        try:
            result = self._client.Trade.Trade_getBucketed(
                symbol=instrument, reverse=False, count=self._limit, binSize=timeframe, startTime=closeDate).result()[0]
        except bravado.exception.HTTPTooManyRequests as err:
            print("To many requests, try again later.")
            result = []

        candles = [candle for candle in result if candle["open"]] # Filter bad data

        # compute open and close times of each candle
        for candle in candles:
            candle["open_datetime_utc"] = candle['timestamp'] - timedelta(timeframe)
            candle["close_datetime_utc"] = candle['timestamp'] - timedelta('1s')
            candle["trade_count"] = candle["trades"]

        return candle_list_to_dataframe(candles)
    
    def get_timeframes(self):
        return [ "1d", "1h", "5m", "1m" ]
    
    def get_instruments(self):
        return [ _["symbol"] for _ in self._client.Instrument.Instrument_getActive().result()[0] ]