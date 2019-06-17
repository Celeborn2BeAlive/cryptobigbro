import argparse, os, time, json
import pandas as pd
from datetime import datetime, timezone
from utils import ensure_mkdir, origin_of_time, timedelta, compute_end_timestamp, string_list_arg, to_comma_separated_string
from exchanges import make_bitmex_exchange, make_binance_exchange, make_coinbasepro_exchange
import pprint

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
    fetch_ohlcv_parser.add_argument(
        '--delay',
        type=int,
        default=1000,
        help='Time to wait in milliseconds between requests. Default to 1000.'
    )

    commands.add_parser("list-instruments") \
        .add_argument(
            'exchange', help='Name of the exchange, eg. bitmex, binance, coinbasepro, etc.'
        )

    commands.add_parser("list-assets") \
        .add_argument(
            'exchange', help='Name of the exchange, eg. bitmex, binance, coinbasepro, etc.'
        )

    commands.add_parser("tickers") \
        .add_argument(
            'exchange', help='Name of the exchange, eg. bitmex, binance, coinbasepro, etc.'
        )

    instrument_info_parser = commands.add_parser("instrument-info")
    instrument_info_parser.add_argument(
        'exchange', help='Name of the exchange, eg. bitmex, binance, coinbasepro, etc.'
    )
    instrument_info_parser.add_argument(
        'instrument', help='Name of the instrument'
    )

    list_timeframes_parser = commands.add_parser("list-timeframes")
    list_timeframes_parser.add_argument(
        'exchange', help='Name of the exchange, eg. bitmex, binance, coinbasepro, etc.'
    )

    time_parser = commands.add_parser("time")
    time_parser.add_argument(
        'exchange', help='Name of the exchange, eg. bitmex, binance, coinbasepro, etc.'
    )

    timestamp_parser = commands.add_parser("timestamp")
    timestamp_parser.add_argument(
        'exchange', help='Name of the exchange, eg. bitmex, binance, coinbasepro, etc.'
    )

    list_exchanges_parser = commands.add_parser("list-exchanges")

    return parser.parse_args()

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

    if args.action == "time":
        print(exchange.get_utc_time())
        exit(0)

    if args.action == "timestamp":
        print(exchange.get_utc_timestamp())
        exit(0)

    if args.action == "list-instruments":
        print(to_comma_separated_string(exchange.get_instruments()))
        exit(0)
    
    if args.action == "list-timeframes":
        print(to_comma_separated_string(exchange.get_timeframes()))
        exit(0)

    if args.action == "list-assets":
        print(to_comma_separated_string(exchange.get_assets()))
        exit(0)

    if args.action == "tickers":
        print(exchange.get_tickers())
        exit(0)

    if args.action == "instrument-info":
        exchange_instruments = exchange.get_instruments()
        if not args.instrument in exchange_instruments:
            print("[ERROR] Unsupported instrument {} for exchange {}.".format(args.instrument, args.exchange))
            exit(-1)
        instrument_info = exchange.get_instrument_info(args.instrument)
        d = {
            "instrument": instrument_info.__dict__
        }
        if args.exchange != "bitmex":
            d["base_asset"] = exchange.get_asset_info(instrument_info.base_asset).__dict__
            d["quote_asset"] = exchange.get_asset_info(instrument_info.quote_asset).__dict__
        print(json.dumps(d, indent=4))
        exit(0)

    assert(args.action == "fetch-ohlcv")

    ensure_mkdir(args.folder)

    timeframes = args.timeframes if args.timeframes else exchange.get_timeframes()
    instruments = args.instruments if args.instruments else exchange.get_instruments()

    exchange_timeframes = exchange.get_timeframes()
    exchange_instruments = exchange.get_instruments()
    exchange_time = exchange.get_utc_time()

    print("Exchange {} at time {}.".format(args.exchange, exchange_time))

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

            next_open_date = compute_end_timestamp(since, tf) + timedelta('1s')
            if exchange_time < next_open_date:
                print("\t\t-- Exchange time is {} and next candle time is {}, no request needed.".format(exchange_time, since + td))
                continue 

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

                time.sleep(args.delay / 1000.0)  # ensure we don't flood exchange API with requests

if __name__ == "__main__":
    main()