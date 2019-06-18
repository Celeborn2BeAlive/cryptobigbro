import argparse, json
from flask import Flask, render_template
import time, threading, math
from threading import Thread, Event
from pprint import pprint
from exchanges import make_exchange
from utils import period_to_seconds, seconds_to_days_hours_minutes_seconds
from datetime import datetime, timedelta
import dateutil.parser

def parse_cli_args():
    parser = argparse.ArgumentParser(description='Crypto Big Bro Investor - Buy cryptocurrencies with FIAT monney')
    
    parser.add_argument('config', type=str, help='Path to a json configuration file')
    parser.add_argument('-p', '--port', type=int, help='Port for the web interface/API')

    return parser.parse_args()

class InvestorThread(Thread):
    def __init__(self, exchange, config):
        Thread.__init__(self)
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

        self.event = Event()

    def get_seconds_remaining(self):
        current_timestamp = time.time()
        seconds_since_origin = current_timestamp - self.invest_time_origin.timestamp()
        previous_period_idx = math.floor(seconds_since_origin / self.invest_period_seconds)
        next_period_timestamp = self.invest_time_origin.timestamp() + (previous_period_idx + 1) * self.invest_period_seconds
        return next_period_timestamp -  current_timestamp, datetime.fromtimestamp(next_period_timestamp)

    def invest(self):
        print("Investing {}".format(self.invest_count))
        print(time.time())
        fiat_account = self.exchange.get_account(self.fiat_currency_account_id)
        if fiat_account['balance'] < self.min_fiat_currency:
            print("Fiat account balance is too low")
            return

        remaining_assets_to_buy = []
        # Iterate on assets to buy and submit orders; if reject put it in remaining_assets_to_buy
        self.assets_to_buy = remaining_assets_to_buy

        while len(self.pending_orders) > 0:
            pass
        
        self.invest_count += 1

    def run(self):
        accounts = self.exchange.get_accounts()
        self.fiat_currency_account_id = next(filter(lambda a: a["currency"] == "EUR", accounts))["id"]

        self.assets_to_buy = []
        self.pending_orders = []

        seconds, next_period_datetime = self.get_seconds_remaining()

        self.event.wait(seconds)
        while not self.event.is_set():
            self.invest()
            self.event.wait(self.invest_period_seconds)

        print("Bye !")

    def stop(self):
        self.event.set()

def make_flask_app(investor):
    app = Flask(__name__)

    @app.route('/')
    def route_index():
        total_seconds_remaining, next_buying_time = investor.get_seconds_remaining()
        days, hours, minutes, seconds = seconds_to_days_hours_minutes_seconds(total_seconds_remaining)
        return render_template('investor/index.html',
            fake=investor.fake,
            nextBuyingTime=str(next_buying_time),
            days=int(days),
            hours=int(hours),
            minutes=int(minutes),
            seconds=int(seconds),
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

    exchange = make_exchange(config["exchange"])

    investor = InvestorThread(exchange, config)

    app = make_flask_app(investor)

    investor.start()

    app.run(debug=True, threaded=True, use_reloader=False)

    investor.stop()
    investor.join()

main()