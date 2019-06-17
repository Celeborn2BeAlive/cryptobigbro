import argparse, json
from flask import Flask, render_template
import time, threading
from threading import Thread
from pprint import pprint
from exchanges import make_coinbasepro_exchange
from utils import period_to_seconds
from datetime import datetime
import dateutil.parser

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
        self.loop_period_seconds = period_to_seconds(config['loopPeriod'])
        self.invest_amount = float(config["investAmount"])
        self.base_currency = config["baseCurrency"]
        self.limit_base_currency = config["limitBaseCurrency"]
        self.print_state_period = config["printStatePeriod"]
        self.fake = config["fake"]
        self.invest_time_origin = dateutil.parser.parse(config["investTimeOrigin"])
    
    def run(self):
        loop_index = 0
        while not self.done:
            loop_index += 1
            time.sleep(self.loop_period_seconds)
        print("Bye !")

def make_flask_app(investor):
    app = Flask(__name__)

    @app.route('/')
    def route_index():
        return str(investor.invest_period_seconds)

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