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
        'volume': []
    }
    index = []

    for candle in candles:
        for item in candle_fields:
            data_dict[item].append(candle[item])
        data_dict['close_timestamp_utc'].append(int(candle["close_datetime_utc"].timestamp()))
        index.append(int(candle["open_datetime_utc"].timestamp()))

    df = pd.DataFrame(data_dict, index=index)
    df.index.name = "open_timestamp_utc"

    return df

def compute_end_timestamp(exchange_now, timeframe):
    if timeframe == "1M":
        # Special case for month because it has not fixed timedelta
        return datetime(exchange_now.year, exchange_now.month, 1, tzinfo=timezone.utc) - timedelta('1s')

    td = timedelta(timeframe)
    start_of_current_bar = int(exchange_now.timestamp() / td.total_seconds()) * td.total_seconds()
    return datetime.fromtimestamp(start_of_current_bar, timezone.utc) - timedelta('1s')

def string_list_arg(string):
    return string.split(',')

def to_comma_separated_string(container):
    s = ""
    for e in container:
        s += e + ","
    return s[:-1]

# period should be something like 1m, 1h, 2d, etc
def period_to_seconds(period):
    number = int(period[0:len(period) - 1])
    suffix = period[len(period) - 1:]
    multiplier = timedeltas_timeframe_suffixes[suffix].total_seconds()
    return number * multiplier

def seconds_to_days_hours_minutes_seconds(total_seconds):
    days = total_seconds // period_to_seconds("1d")
    total_seconds = total_seconds % period_to_seconds("1d")
    hours = total_seconds // period_to_seconds("1h")
    total_seconds = total_seconds % period_to_seconds("1h")
    minutes = total_seconds // period_to_seconds("1m")
    total_seconds = total_seconds % period_to_seconds("1m")
    seconds = total_seconds
    return days, hours, minutes, seconds

def list_to_dict(l, key):
    return { e[key]: e for e in l }