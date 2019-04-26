from datetime import datetime, timezone, timedelta
import os
import pandas as pd

origin_of_time = datetime(1970, 1, 1, tzinfo=timezone.utc)

timedeltas_timeframe_suffixes = {
    "s": timedelta(seconds=1),
    "m": timedelta(minutes=1),
    "h": timedelta(hours=1),
    "d": timedelta(days=1),
    "w": timedelta(days=7)
}

def timedelta(timeframe):
    for suffix in timedeltas_timeframe_suffixes.keys():
        if timeframe.endswith(suffix):
            _ = timeframe.split(suffix)
            c = int(_[0])
            return c * timedeltas_timeframe_suffixes[suffix]
    print("Unable to convert timeframe {} to a fixed timedelta.".format(timeframe))

def ensure_mkdir(p):
    if not os.path.exists(p):
        os.mkdir(p)
    else:
        if not os.path.isdir(p):
            raise RuntimeError("{} is not a directory.".format(p))

def candle_list_to_dataframe(candles):
    if len(candles) == 0:
        return pd.DataFrame()

    candle_fields = [
        'open', 'high', 'low', 'close', 'volume'
    ]

    data_dict = {
        'close_timestamp_utc': [],
        'open': [],
        'high': [],
        'low': [],
        'close': [],
        'volume': [],
        'quote_volume': []
    }
    index = []

    for candle in candles:
        for item in candle_fields:
            data_dict[item].append(candle[item])
        data_dict['close_timestamp_utc'].append(int(candle["close_datetime_utc"].timestamp()))
        if 'quote_volume' in candle.keys():
            data_dict['quote_volume'].append(candle["quote_volume"])
        index.append(int(candle["open_datetime_utc"].timestamp()))

    df = pd.DataFrame(data_dict, index=index)
    df.index.name = "open_timestamp_utc"

    return df