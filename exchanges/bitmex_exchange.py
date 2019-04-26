import bitmex
import bravado
import pandas as pd

from utils import timedelta, candle_list_to_dataframe

# API used: https://github.com/BitMEX/api-connectors/tree/master/official-http/python-swaggerpy

class BitmexExchange:
    def __init__(self):
        self._client = bitmex.bitmex(test=False)
        self._limit = 750 # Max number of candles that bitmex is sending
    
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