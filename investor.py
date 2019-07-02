import argparse, json
from flask import Flask, render_template
import time, threading, math
from threading import Thread, Event
from pprint import pprint
from exchanges import make_exchange
from utils import period_to_seconds, seconds_to_days_hours_minutes_seconds
from datetime import datetime, timedelta
import dateutil.parser
import logging # https://realpython.com/python-logging/
import os

log_filename = "investor-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".html"

def dict_to_html(d):
    s = "<table>"
    for k in d:
        s += "<tr><td>" + str(k) + "</td><td>" + str(d[k]) + "</td></tr>"
    s += "</table>"
    return s

def parse_cli_args():
    parser = argparse.ArgumentParser(description='Crypto Big Bro Investor - Buy cryptocurrencies with FIAT monney')
    
    parser.add_argument('config', type=str, help='Path to a json configuration file')
    parser.add_argument('-p', '--port', type=int, default=5000, help='Port for the web interface/API')
    parser.add_argument('-l', '--log-dir', type=str, help='Path to a directory that should contains the log file')

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

    def place_order(self, asset):
        instr = self.exchange.get_instrument_name(asset, self.fiat_currency)
        orders = self.exchange.get_order_book(instr, level=1)
        buy_price = float(orders['bids'][0][0]) 
        if self.fake:
            buy_price = buy_price * 0.5 # half bid price to ensure testing for now (the order will not be immediately filled)
        buy_price_base = round(buy_price * 100) / 100
        size = self.invest_amount[asset] / buy_price
        size_btc = round(size * 10e7) / 10e7
        buy_size = self.exchange.clamp_to_min_max(instr, size_btc)

        return self.exchange.place_buy_order(instrument=instr, price=buy_price_base, size=buy_size, post_only=True, time_in_force='GTT', cancel_after=self.cancel_after)

    def place_orders_for_assets_to_buy(self):
        remaining_assets_to_buy = []
        for asset in self.assets_to_buy:
            result = self.place_order(asset)
            if result["status"] == "pending" or result["status"] == "open":
                self.pending_orders.append(result)
            else:
                logging.warning(f'Unknown status {result["status"]}')
            logging.info("Place order<br>" + dict_to_html(result))

        self.assets_to_buy = remaining_assets_to_buy

    def cancel_pending_orders(self):
        for order in self.pending_orders:
            try:
                self.exchange.cancel_order(order["id"])
            except e:
                logging.error(f'{e}')

    def invest(self):
        logging.info("Investing {}".format(self.invest_count))
        fiat_account = self.exchange.get_account(self.fiat_currency_account_id)
        if fiat_account['balance'] < self.min_fiat_currency:
            logging.error("Fiat account balance is too low")
            return

        self.place_orders_for_assets_to_buy()

        while len(self.pending_orders) > 0 and not self.event.is_set():
            open_orders = []
            for order in self.pending_orders:
                result = self.exchange.get_order(order["id"])
                if "status" in result:
                    if result["status"] == "open":
                        open_orders.append(order)
                    else:
                        logging.info("Order filled<br>" + dict_to_html(result))
                else:
                    logging.info("Order canceled<br>" + dict_to_html(order))
                    # order cancelled, need to try again
                    self.assets_to_buy.append(order["product_id"].split("-")[0])
            self.pending_orders = open_orders

            self.place_orders_for_assets_to_buy()

            time.sleep(1)
        
        self.invest_count += 1

    def run(self):
        accounts = self.exchange.get_accounts()
        self.fiat_currency_account_id = next(filter(lambda a: a["currency"] == "EUR", accounts))["id"]

        self.assets_to_buy = []
        self.pending_orders = []

        seconds, next_period_datetime = self.get_seconds_remaining()

        print(f'Time until first investment: {seconds} seconds')
        logging.warning(f'Time until first investment: {seconds} seconds')

        self.event.wait(seconds)
        while not self.event.is_set():
            self.assets_to_buy = self.invest_amount.keys()
            self.invest()
            self.event.wait(self.invest_period_seconds)

        self.cancel_pending_orders()
        logging.info("Bye !")

    def stop(self):
        self.event.set()

def make_flask_app(investor):
    app = Flask(__name__)

    # Disable werkzeug logging
    app.logger.disabled = True
    log = logging.getLogger('werkzeug')
    log.disabled = True

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

    @app.route('/log')
    def route_log():
        with open(log_filename) as f:
            return "".join(reversed(f.readlines()))

    return app

def main():
    global log_filename

    args = parse_cli_args()
    if args.log_dir:
        log_filename = os.path.join(args.log_dir, log_filename)

    logging.basicConfig(filename=log_filename, filemode='w', format='<p>%(asctime)s - %(levelname)s - %(message)s</p>', level=logging.INFO)
    logging.info(f'Logging to file {log_filename}')

    with open(args.config) as f:
        config = json.load(f)
    
    pprint(config)

    exchange = make_exchange(config["exchange"])

    investor = InvestorThread(exchange, config)

    app = make_flask_app(investor)

    investor.start()

    app.run(port=args.port, debug=True, threaded=True, use_reloader=False)

    investor.stop()
    investor.join()

main()