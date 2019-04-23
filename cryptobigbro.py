import argparse, os, time
import pandas as pd
from datetime import datetime, timezone
from utils import timedeltas, ensure_mkdir
from exchanges import BitmexExchange

def parse_cli_args():
    parser = argparse.ArgumentParser(description='crypto big bro')
    parser.add_argument(
        'exchange', help='Name of the exchange, eg. bitmex, binance, coinbasepro, etc.'
    )
    parser.add_argument(
        'instrument', help='Name of the instrument, eg. XBTUSD, ETHBTC, etc. Depends on the exchange.'
    )
    parser.add_argument(
        'folder', help='Path to the folder where OHLCV csv files should be stored.'
    )
    parser.add_argument(
        '--timeframes', help='A comma separated list of timeframes. If not provided, all timeframes provided by the exchange will be fetch.'
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_cli_args()

    exchange = BitmexExchange()
    print(exchange.get_instruments())

    ensure_mkdir(args.folder)
    
    timeframes = exchange.get_timeframes()

    for tf in timeframes:
        path_to_csv_file = os.path.join(args.folder, args.exchange + "-" + args.instrument + "-" + tf + ".csv")

        if (os.path.exists(path_to_csv_file)):
            print("Load existing history {} to get next timestamp".format(path_to_csv_file))
            df = pd.read_csv(path_to_csv_file, index_col='open_timestamp')
            since = datetime.utcfromtimestamp(df.index[-1]) + timedeltas[tf]
        else:
            since = datetime(1970, 1, 1, tzinfo=timezone.utc)

        while True:
            print("Fetching ohlcv candles for timeframe {} since {}".format(tf, since))
            df = exchange.fetch_ohlcv(timeframe=tf, since=since, instrument=args.instrument)

            print("{} ohlcv candles received.".format(len(df)))

            if df.empty:
                print("No candles received for timeframe {}, work is done.".format(tf))
                break

            df.to_csv(path_to_csv_file, index_label='open_timestamp', mode='a', header=not os.path.exists(path_to_csv_file))

            since = datetime.utcfromtimestamp(df.index[-1]) + timedeltas[tf]

            time.sleep(1)  # ensure we don't flood exchange API with requests