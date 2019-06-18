import argparse, json
from flask import Flask, render_template
import time, threading
from threading import Thread, Timer
from pprint import pprint
from exchanges import make_coinbasepro_exchange
from utils import period_to_seconds
from datetime import datetime, timedelta
import dateutil.parser
import math, time

def parse_cli_args():
    parser = argparse.ArgumentParser(description='Crypto Big Bro Investor - Buy cryptocurrencies with FIAT monney')
    
    parser.add_argument('config', type=str, help='Path to a json configuration file')
    parser.add_argument('-p', '--port', type=int, help='Port for the web interface/API')

    return parser.parse_args()

class InvestorThread(Thread):
    def __init__(self, exchange, config):
        Thread.__init__(self)
        self.done = False
        self.exchange = exchange
        self.config = config
        self.invest_period_seconds = period_to_seconds(config['investPeriod'])
        self.invest_amount = config["investAmount"]
        self.fiat_currency = config["fiatCurrency"]
        self.min_fiat_currency = config["minFiatCurrency"]
        self.print_state_period = config["printStatePeriod"]
        self.fake = config["fake"] if "fake" in config else False
        self.invest_time_origin = dateutil.parser.parse(config["investTimeOrigin"])
        self.cancel_after = config["cancelAfter"]
        self.invest_count_limit = config["investCountLimit"] if "investCountLimit" in config else 0

        self.get_seconds_remaining()

        self.invest_count = 0

    def get_seconds_remaining(self):
        seconds_since_origin = time.time() - self.invest_time_origin.timestamp()
        previous_period_idx = math.floor(seconds_since_origin / self.invest_period_seconds)
        self.next_period_timestamp = self.invest_time_origin.timestamp() + (previous_period_idx + 1) * self.invest_period_seconds
        self.current_timestamp = time.time()
        self.seconds_remaining = max(0, self.next_period_timestamp -  self.current_timestamp)
        return self.seconds_remaining

    def run(self):
        accounts = self.exchange.get_accounts()
        fiat_currency_account_id = next(filter(lambda a: a["currency"] == "EUR", accounts))["id"]

        self.get_seconds_remaining()

        assets_to_buy = []
        pending_orders = []

        loop_index = 0
        while not self.done:
            loop_index += 1
            self.current_timestamp = time.time()
            self.seconds_remaining = max(0, self.next_period_timestamp -  self.current_timestamp)
            print(self.seconds_remaining)

            if len(pending_orders) > 0:
                pass # should find which orders are still open

            fiat_account = self.exchange.get_account(fiat_currency_account_id)
            if fiat_account['balance'] < self.min_fiat_currency:
                print("Fiat account balance is too low")
                continue
            
            remaining_assets_to_buy = []
            # Iterate on assets to buy and submit orders; if reject put it in remaining_assets_to_buy
            assets_to_buy = remaining_assets_to_buy

            if len(assets_to_buy) == 0 and len(pending_orders) == 0 and self.seconds_remaining == 0 and \
                (self.invest_count_limit == 0 or self.invest_count < self.invest_count_limit):
                assets_to_buy = self.invest_amount.keys()
                previous_period_idx = math.floor((self.current_timestamp - self.invest_time_origin.timestamp()) / self.invest_period_seconds)
                self.next_period_timestamp = self.invest_time_origin.timestamp() + (previous_period_idx + 1) * self.invest_period_seconds
                self.invest_count += 1
            
            time.sleep(1)
        print("Bye !")

def make_flask_app(investor):
    app = Flask(__name__)

    @app.route('/')
    def route_index():
        next_buying_time = datetime.fromtimestamp(investor.next_period_timestamp)
        total_seconds_remaining = investor.seconds_remaining
        days = math.floor(total_seconds_remaining / period_to_seconds("1d"))
        total_seconds_remaining -= days * period_to_seconds("1d")
        hours = math.floor(total_seconds_remaining / period_to_seconds("1h"))
        total_seconds_remaining -= hours * period_to_seconds("1h")
        minutes = math.floor(total_seconds_remaining / period_to_seconds("1m"))
        total_seconds_remaining -= minutes * period_to_seconds("1m")
        seconds = total_seconds_remaining
        return render_template('investor/index.html',
            fake=investor.fake,
            nextBuyingTime=str(next_buying_time),
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            investCount=investor.invest_count,
            investCountLimit=investor.invest_count_limit,
            assetInfo=[],
            assetsToBuy=[]
        )

    @app.route('/accounts')
    def route_accounts():
        accounts = [ a for a in investor.exchange.get_accounts() if a['balance'] > 0.0 ]
        total_value = 0
        for a in accounts:
            a['value'] = a['balance'] * investor.exchange.get_price(a['currency'], 'EUR') if a['currency'] != 'EUR' else a['balance']
            total_value += a['value']
        for a in accounts:
            a['percentage'] = 100.0 * a['value'] / total_value
        return render_template('investor/accounts.html', accounts=accounts)

    return app

def main():
    args = parse_cli_args()

    with open(args.config) as f:
        config = json.load(f)
    
    pprint(config)

    exchange = make_coinbasepro_exchange(api_key=config)

    investor = InvestorThread(exchange, config)

    app = make_flask_app(investor)

    investor.start()

    app.run(debug=True, threaded=True, use_reloader=False)

    investor.done = True
    investor.join()

main()