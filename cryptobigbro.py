import argparse, os, time
import pandas as pd
from datetime import datetime, timezone
from utils import ensure_mkdir, origin_of_time
from exchanges import make_bitmex_exchange, make_binance_exchange, make_coinbasepro_exchange
import pprint

def string_list_arg(string):
    return string.split(',')

def parse_cli_args():
    parser = argparse.ArgumentParser(description='Crypto Big Bro - Spy OHLCV data from crypto exchanges.')
    commands = parser.add_subparsers(title="sub-commands", dest="action")

    fetch_ohlcv_parser = commands.add_parser("fetch-ohlcv")
    fetch_ohlcv_parser.add_argument(
        'exchange', help='Name of the exchange, eg. bitmex, binance, coinbasepro, etc.'
    )
    fetch_ohlcv_parser.add_argument(
        'instrument', help='Name of the instrument, eg. XBTUSD, ETHBTC, etc. Depends on the exchange.'
    )
    fetch_ohlcv_parser.add_argument(
        'folder', help='Path to the folder where OHLCV csv files should be stored.'
    )
    fetch_ohlcv_parser.add_argument(
        '--timeframes',
        type=string_list_arg,
        help='A comma separated list of timeframes. If not provided, all timeframes provided by the exchange will be fetch.'
    )

    list_instruments_parser = commands.add_parser("list-instruments")
    list_instruments_parser.add_argument(
        'exchange', help='Name of the exchange, eg. bitmex, binance, coinbasepro, etc.'
    )

    list_timeframes_parser = commands.add_parser("list-timeframes")
    list_timeframes_parser.add_argument(
        'exchange', help='Name of the exchange, eg. bitmex, binance, coinbasepro, etc.'
    )

    list_exchanges_parser = commands.add_parser("list-exchanges")

    return parser.parse_args()

if __name__ == "__main__":
    # pp = pprint.PrettyPrinter(indent=4)

    args = parse_cli_args()

    exchanges = {
        "bitmex": make_bitmex_exchange,
        "binance": make_binance_exchange,
        "coinbasepro": make_coinbasepro_exchange
    }

    if args.action == "list-exchanges":
        print(list(exchanges.keys()))
        exit(0)

    if args.exchange in exchanges.keys():
        exchange = exchanges[args.exchange]()
    else:
        print("Unsupported exchange {}".format(args.exchange))
        exit(-1)

    if args.action == "list-instruments":
        print(exchange.get_instruments())
        exit(0)
    
    if args.action == "list-timeframes":
        print(exchange.get_timeframes())
        exit(0)

    assert(args.action == "fetch-ohlcv")

    ensure_mkdir(args.folder)
    
    if args.timeframes:
        timeframes = args.timeframes
    else:
        timeframes = exchange.get_timeframes()

    exchange_timeframes = exchange.get_timeframes()

    for tf in timeframes:
        if not tf in exchange_timeframes:
            print("Unsupported timeframe {} for exchange {}.".format(tf, args.exchange))
            continue

        path_to_csv_file = os.path.join(args.folder, args.exchange + "-" + args.instrument + "-" + tf + ".csv")

        since = origin_of_time
        if (os.path.exists(path_to_csv_file)):
            print("Load existing history {} to get next timestamp".format(path_to_csv_file))
            df = pd.read_csv(path_to_csv_file, index_col='open_timestamp')
            since = datetime.fromtimestamp(df.close_timestamp_utc.values[-1], timezone.utc)
            
        while True:
            print("Fetching ohlcv candles for timeframe {} since {}".format(tf, since))
            df = exchange.fetch_ohlcv(timeframe=tf, since=since, instrument=args.instrument)
            print("{} ohlcv candles received.".format(len(df)))

            if df.empty:
                print("No candles received for timeframe {}, work is done.".format(tf))
                break

            df.to_csv(path_to_csv_file, index_label='open_timestamp', mode='a', header=not os.path.exists(path_to_csv_file))
            since = datetime.fromtimestamp(df.close_timestamp_utc.values[-1], timezone.utc)

            time.sleep(1)  # ensure we don't flood exchange API with requests