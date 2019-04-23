from datetime import datetime, timezone, timedelta
import os
import pandas as pd

timedeltas = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1)
}

def ensure_mkdir(p):
    if not os.path.exists(p):
        os.mkdir(p)
    else:
        if not os.path.isdir(p):
            raise RuntimeError("{} is not a directory.".format(p))

def candle_list_to_dataframe(candles):
    if len(candles) == 0:
        return pd.DataFrame()

    data_dict = {
        'close': [],
        'open': [],
        'high': [],
        'low': [],
        'volume': []
    }
    index = []

    for candle in candles:
        for item in data_dict.keys():
            data_dict[item].append(candle[item])
        index.append(int(candle["openDate"].timestamp()))

    df = pd.DataFrame(data_dict, index=index)
    df.index.name = "open_timestamp"

    return df