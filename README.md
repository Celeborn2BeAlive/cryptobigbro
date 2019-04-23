# Crypto Big Bro

A python tool to maintain a local OHLCV candles history of crypto instruments for various exchanges.

For now the repository is in a Work in Progress state. See Todo section below for the list of things that I must implement before having it ready.

# Goal

TODO: explain what this repository is for

# Setup

TODO (pip install etc.)

# Usage

python cryptobigbro ACTION EXCHANGE INSTRUMENT FOLDER [--timeframes TIMEFRAMELIST]

Examples:

- python cryptobigbro fetch-ohlcv bitmex XBTUSD /home/me/bitmex-XBTUSD-history
- python cryptobigbro fetch-ohlcv binance ETHBTC /home/me/binance-ETHBTC-history --timeframes 1m,30m,1d
- python cryptobigbro list-instruments coinbasepro
- python cryptobigbro list-timeframes binance
- python cryptobigbro list-exchanges

# CSV Files

List columns

# Done

- Fetch OHLCV candles from bitmex and store them in csv files.

# Todo

- Handle timeframes in command line
- Implement more exchanges (at least binance and coinbasepro)
- Provide the possibility to list instruments and timeframes from a given exchange
- Provide the possibility to list exchanges
- Better README.md