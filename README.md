# Crypto Big Bro

A python tool to maintain a local OHLCV candles history of crypto instruments for various exchanges.

# Goal

The goal is to gather a lot of OHLCV data from crypto exchanges for analysis and crypto trading/investing.

# Setup

In a clone of the repository, run the following commands to install a python 3 virtual environment for running the script:

```bash
virtualenv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

# Usage

python cryptobigbro ACTION EXCHANGE INSTRUMENT FOLDER [--timeframes TIMEFRAMELIST]

Examples:

- python cryptobigbro fetch-ohlcv bitmex XBTUSD /home/me/bitmex-XBTUSD-history
- python cryptobigbro fetch-ohlcv binance ETHBTC /home/me/binance-ETHBTC-history --timeframes 1m,30m,1d
- python cryptobigbro list-instruments coinbasepro
- python cryptobigbro list-timeframes binance
- python cryptobigbro list-exchanges

# CSV Files

The fetch-ohlcv command update a file 'EXCHANGE-INSTRUMENT.csv' in the folder specified on the command line. If the file or the folder do not exist, they are created.

The columns of the CSV file are open_timestamp_utc, close_timestamp_utc, open, high, low, close and volume.

Timestamps are in seconds and in UTC timezone.

# Todo

- Implement more exchanges (at coinbasepro)
- Better README.md
- Store information about each product in a json file