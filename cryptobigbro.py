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
        '--instruments',
        type=string_list_arg,
        help='Name of instruments to fetch data, eg. XBTUSD, ETHBTC, etc. Depends on the exchange. If not provided, all instruments provided by the exchange will be fetched.'
    )
    fetch_ohlcv_parser.add_argument(
        'folder', help='Path to the folder where OHLCV csv files should be stored.'
    )
    fetch_ohlcv_parser.add_argument(
        '--timeframes',
        type=string_list_arg,
        help='A comma separated list of timeframes. If not provided, all timeframes provided by the exchange will be fetched.'
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

def to_comma_separated_string(container):
    s = ""
    for e in container:
        s += e + ","
    return s[:-1]

def main():
    # pp = pprint.PrettyPrinter(indent=4)

    args = parse_cli_args()

    exchanges = {
        "bitmex": make_bitmex_exchange,
        "binance": make_binance_exchange,
        "coinbasepro": make_coinbasepro_exchange
    }

    if args.action == "list-exchanges":
        print(to_comma_separated_string(exchanges.keys()))
        exit(0)

    if args.exchange in exchanges.keys():
        exchange = exchanges[args.exchange]()
    else:
        print("Unsupported exchange {}".format(args.exchange))
        exit(-1)

    if args.action == "list-instruments":
        print(to_comma_separated_string(exchange.get_instruments()))
        exit(0)
    
    if args.action == "list-timeframes":
        print(to_comma_separated_string(exchange.get_timeframes()))
        exit(0)

    assert(args.action == "fetch-ohlcv")

    ensure_mkdir(args.folder)

    timeframes = args.timeframes if args.timeframes else exchange.get_timeframes()
    instruments = args.instruments if args.instruments else exchange.get_instruments();

    exchange_timeframes = exchange.get_timeframes()
    exchange_instruments = exchange.get_instruments();

    print("Exchange {}.".format(args.exchange))

    for instrument in instruments:
        if not instrument in exchange_instruments:
            print("[ERROR] Unsupported instrument {} for exchange {}.".format(instrument, args.exchange))
            continue

        print("-- Fetching data for instrument {}.".format(instrument))

        for tf in timeframes:
            if not tf in exchange_timeframes:
                print("[ERROR] Unsupported timeframe {} for exchange {}.".format(tf, args.exchange))
                continue

            print("\t-- Fetching data for timeframe {}.".format(tf))

            path_to_csv_file = os.path.join(args.folder, args.exchange + "-" + instrument + "-" + tf + ".csv")

            since = origin_of_time
            if (os.path.exists(path_to_csv_file)):
                print("\t\t-- Loading existing history from file {} to get next timestamp.".format(path_to_csv_file))
                df = pd.read_csv(path_to_csv_file, index_col='open_timestamp_utc')
                since = datetime.fromtimestamp(df.close_timestamp_utc.values[-1], timezone.utc)
                
            while True:
                print("\t\t-- Fetching candles since {}".format(since))
                df = exchange.fetch_ohlcv(timeframe=tf, since=since, instrument=instrument)
                
                if df.empty:
                    print("\t\t-- No candles received for timeframe {}, work is done.".format(tf))
                    break
                else:
                    print("\t\t-- {} candles received.".format(len(df)))

                df.to_csv(path_to_csv_file, index_label='open_timestamp_utc', mode='a', header=not os.path.exists(path_to_csv_file))
                since = datetime.fromtimestamp(df.close_timestamp_utc.values[-1], timezone.utc)

                time.sleep(1)  # ensure we don't flood exchange API with requests

if __name__ == "__main__":
    main()