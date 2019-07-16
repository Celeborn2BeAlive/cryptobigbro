import argparse, json
from flask import Flask, render_template
from pprint import pprint
from exchanges import make_exchange
from utils import list_to_dict
import os

def parse_cli_args():
    parser = argparse.ArgumentParser(description='Crypto Big Bro Coinbasepro Account History')
    
    parser.add_argument('config', type=str, help='Path to a json configuration file')
    parser.add_argument('-p', '--port', type=int, default=5000, help='Port for the web interface/API')
    parser.add_argument('-c', '--cache-file', type=str, help='Path to a file to store history')

    return parser.parse_args()

class CpbroHistory:
    def __init__(self, exchange):
        self.exchange = exchange

        self.histories = {} # for each account store its history
        self.transfers = {} # for each account, the list of its transfers
        self.orders = {}
        self.current_version = 0

        self.cache_filepath = None
    
    def load_from_cache(self, filepath):
        self.cache_filepath = filepath
        if not os.path.exists(filepath):
            return
        with open(filepath, "r") as f:
            cache = json.load(f)
            self.histories = cache["histories"]
            self.transfers = cache["transfers"]
            self.orders = cache["orders"]
            version = 0 if not "version" in cache else cache["version"]
            if version != self.current_version:
                self.update_from_version(version)
    
    def compute_additional_data(self, account_id):
        balance = 0
        average_unit_cost = 0
        for event in reversed(self.histories[account_id]):
            new_balance =  float(event["balance"])
            if event["type"] == "match":
                if "average_unit_cost" in event["details"]:
                    average_unit_cost = event["details"]["average_unit_cost"]
                    continue
                order = self.orders[event["details"]["order_id"]]
                amount = abs(float(event["amount"]))
                executed_price = float(order["executed_price"])
                if order["side"] == "buy":
                    new_average_unit_cost = (balance * average_unit_cost + amount * executed_price) / new_balance
                    event["details"]["average_unit_cost"] = new_average_unit_cost
                else:
                    new_average_unit_cost = average_unit_cost if new_balance > 0 else 0
                    cost = amount * average_unit_cost
                    event["details"]["average_unit_cost"] = new_average_unit_cost
                    event["details"]["profit_and_loss"] = amount * executed_price - cost
                    event["details"]["profit_and_loss_return"] = event["details"]["profit_and_loss"] / cost if cost > 0 else 0
                balance = new_balance
                average_unit_cost = new_average_unit_cost if balance > 0 else 0
            else:
                balance = new_balance
                average_unit_cost = average_unit_cost if balance > 0 else 0

    def compute_order_additional_data(self, order):
        if not "executed_price" in order:
            executed_value = float(order["executed_value"])
            filled_size = float(order["filled_size"])
            order["executed_price"] = executed_value / filled_size

    def update_from_version(self, version):
        return

    def save_to_cache(self):
        if not self.cache_filepath:
            return

        with open(self.cache_filepath, 'w') as f:
            json.dump({
                "version": self.current_version,
                "histories": self.histories,
                "transfers": self.transfers,
                "orders": self.orders
            }, f, indent=4)

    def update(self, account_id):
        if not account_id in self.histories:
            self.histories[account_id] = []

        prev = self.histories[account_id][0]["id"] if len(self.histories[account_id]) > 0 else None
        new_values = self.exchange.get_account_history(account_id, before=prev)
        for event in new_values:
            if event["type"] == "match" or event["type"] == "fee":
                order_id = event["details"]["order_id"]
                if not order_id in self.orders:
                    self.orders[order_id] = self.exchange.get_order(order_id)
                    self.compute_order_additional_data(self.orders[order_id])

        self.histories[account_id] = new_values + self.histories[account_id]

        if not account_id in self.transfers:
            self.transfers[account_id] = []

        prev = self.transfers[account_id][0]["id"] if len(self.transfers[account_id]) > 0 else None
        self.transfers[account_id] = self.exchange.get_account_transfers(account_id, before=prev) + self.transfers[account_id]

        self.compute_additional_data(account_id)
        self.save_to_cache()

def make_flask_app(exchange, cpbro_history):
    app = Flask(__name__)

    @app.template_filter('round_str_number')
    def round_str_number(s, decimals):
        return round(float(s), decimals)

    @app.route('/')
    def route_index():
        accounts = [ a for a in exchange.get_accounts() if a['balance'] > 0.0 ]
        total_value = 0
        for a in accounts:
            a['value'] = a['balance'] * exchange.get_price(a['currency'], 'EUR') if a['currency'] != 'EUR' else a['balance']
            total_value += a['value']
        for a in accounts:
            a['percentage'] = 100.0 * a['value'] / total_value

        for a in accounts:
            cpbro_history.update(a['id'])

        return render_template('investor/accounts.html', accounts=accounts)

    @app.route('/history/<account_id>')
    def route_history(account_id):
        cpbro_history.update(account_id)
        account = exchange.get_account(account_id)
        history = cpbro_history.histories[account_id]
        transfers = cpbro_history.transfers[account_id]
        return render_template('investor/history.html', account=account, history=history, transfers=transfers)

    @app.route('/orders')
    def route_orders():
        orders = sorted(cpbro_history.orders.values(), key=lambda x: x["created_at"], reverse=True)
        return render_template('investor/orders.html', orders=orders)

    return app

def main():
    args = parse_cli_args()

    with open(args.config) as f:
        config = json.load(f)
    
    exchange = make_exchange(config["exchange"])
    history = CpbroHistory(exchange)

    if args.cache_file:
        history.load_from_cache(args.cache_file)

    app = make_flask_app(exchange, history)

    app.run(host='0.0.0.0', port=args.port, debug=True, threaded=True, use_reloader=False)

main()