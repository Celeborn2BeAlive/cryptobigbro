import argparse, json, os
from flask import Flask, render_template
from pprint import pprint
from exchanges import make_exchange
from utils import list_to_dict, make_logger
from threading import Thread, Event
import logging # https://realpython.com/python-logging/
import shutil, time, datetime

# Todo:
# - Diagrams: percentage diagrams (value, cost, risk)
# - Handle backtest exchange: it takes its price from OHLCV files
# - Curves: daily equity curve, with deposit and withdraw events, and also buy/sell
# - Time slider (or calendar ?)
# - Rebalance tool
# - Update icon
# - Generalize to other exchanges (binance at least, bittrex would be great too)
# - Add cold storage accounts
# - Compute markowitz portfolio weights
# - Backtest

logger = None

def parse_cli_args():
    parser = argparse.ArgumentParser(description='Crypto Big Bro Coinbasepro Account History')
    
    parser.add_argument('config', type=str, help='Path to a json configuration file')
    parser.add_argument('-p', '--port', type=int, default=5000, help='Port for the web interface/API')
    parser.add_argument('-c', '--cache-file', type=str, help='Path to a file to store history')
    parser.add_argument('-l', '--log-file', help='Path to log file')

    return parser.parse_args()

class CpbroHistory:
    def __init__(self, exchange):
        self.exchange = exchange

        self.account_to_currency = {} # for each account, the currency
        self.currency_to_account = {}
        self.histories = {} # for each account store its history
        self.transfers = {} # for each account, the list of its transfers
        self.orders = {}
        self.current_version = 0

        self.cache_filepath = None
    
    def load_from_cache(self, filepath):
        logger.info("Loading cache...")
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
        logger.info("Done.")
    
    def compute_additional_data(self, account_id):
        balance = 0
        average_unit_cost = 0
        currency = self.account_to_currency[account_id]
        for event in reversed(self.histories[account_id]):
            new_balance =  float(event["balance"])
            if event["type"] == "match" and currency != 'EUR':
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
            else:
                if event["type"] == "fee":
                    amount = float(event["amount"])
                    event["details"]["profit_and_loss"] = amount
                new_average_unit_cost = average_unit_cost

            balance = new_balance
            average_unit_cost = new_average_unit_cost if balance > 0 else 0

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

    def get_average_unit_cost(self, currency):
        assert(currency in self.currency_to_account)
        if currency == "EUR":
            return 1
        account_id = self.currency_to_account[currency]
        for event in self.histories[account_id]:
            if 'average_unit_cost' in event['details']:
                return event['details']['average_unit_cost']

    def get_realized_profit_and_loss(self, currency):
        assert(currency in self.currency_to_account)
        account_id = self.currency_to_account[currency]
        profit_and_loss = 0
        for event in self.histories[account_id]:
            if 'profit_and_loss' in event['details']:
                profit_and_loss += event["details"]["profit_and_loss"]
        return profit_and_loss

    def get_total_deposit(self):
        total_deposit = 0
        account_id = self.currency_to_account['EUR']
        for event in self.histories[account_id]:
            if event['type'] == 'transfer' and event['details']['transfer_type'] == 'deposit':
                total_deposit += float(event['amount'])
        return total_deposit
    
    def get_total_withdraw(self):
        total_withdraw = 0
        for account_id in self.histories:
            average_unit_cost = 1 if self.account_to_currency[account_id] == 'EUR' else 0
            for event in self.histories[account_id]:
                if 'average_unit_cost' in event['details']:
                    average_unit_cost = event['details']['average_unit_cost']
                if event['type'] == 'transfer' and event['details']['transfer_type'] == 'withdraw':
                    total_withdraw += abs(float(event['amount'])) * average_unit_cost
        return total_withdraw

    def update(self, account):
        logger.info(f'Updating account {account["id"]} for currency {account["currency"]}')
        account_id = account['id']

        self.currency_to_account[account['currency']] = account_id
        self.account_to_currency[account_id] = account['currency']

        if not account_id in self.histories:
            self.histories[account_id] = []

        prev = self.histories[account_id][0]["id"] if len(self.histories[account_id]) > 0 else None
        new_values = self.exchange.get_account_history(account_id, before=prev)
        logger.info(f'Loaded {len(new_values)} new events for account {account["id"]}({account["currency"]})')
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
        new_transfers = self.exchange.get_account_transfers(account_id, before=prev)
        logger.info(f'Loaded {len(new_transfers)} new transfers for account {account["id"]}({account["currency"]})')
        self.transfers[account_id] = new_transfers + self.transfers[account_id]

        self.compute_additional_data(account_id)
        self.save_to_cache()

def update_all_accounts(exchange, cbpro_history):
    logger.info("Updating all accounts...")
    for account in exchange.get_accounts():
        cbpro_history.update(account)
        yield
    logger.info("Done.")

class CbproHistoryUpdateThread(Thread):
    def __init__(self, exchange, cbpro_history):
        Thread.__init__(self)
        self.event = Event()
        self.cbpro_history = cbpro_history
        self.exchange = exchange
    
    def run(self):
        count = 0
        while not self.event.is_set():
            if count % 60 == 0:
                for _ in update_all_accounts(self.exchange, self.cbpro_history):
                    if self.event.is_set():
                        break
                count = 0
            count += 1
            self.event.wait(1)
        logger.info("Exiting run loop of CbproHistoryUpdateThread. Buy !")
    
    def stop(self):
        self.event.set()

def make_flask_app(exchange, cpbro_history):
    app = Flask(__name__)

    @app.template_filter('round_str_number')
    def round_str_number(s, decimals):
        return round(float(s), decimals)

    @app.route('/')
    @app.route('/accounts')
    def route_accounts():
        accounts = [ a for a in exchange.get_accounts() if a['balance'] > 0.0 ]
        total_value = 0
        for a in accounts:
            a['price'] = exchange.get_price(a['currency'], 'EUR') if a['currency'] != 'EUR' else 1
            a['average_unit_cost'] = cpbro_history.get_average_unit_cost(a['currency'])
            a['return'] = 100 * (a['price'] - a['average_unit_cost']) / a['average_unit_cost']
            a['total_cost'] = a['balance'] * a['average_unit_cost']
            a['realized_pnl'] = cpbro_history.get_realized_profit_and_loss(a['currency'])
            a['value'] = a['balance'] * a['price']
            a['unrealized_pnl'] = a['value'] - a['total_cost']
            total_value += a['value']
        for a in accounts:
            a['percentage'] = 100.0 * a['value'] / total_value

        total_deposit = cpbro_history.get_total_deposit()
        total_withdraw = cpbro_history.get_total_withdraw()
        total_invested = total_deposit - total_withdraw
        total_value = 0
        total_unrealized_pnl = 0
        total_at_risk = 0
        for a in accounts:
            total_value += a['value']
            total_unrealized_pnl += a['unrealized_pnl']
            if a['currency'] != 'EUR':
                total_at_risk += a['value']
        total_return = 100 * (total_value - total_invested) / total_invested if total_invested > 0 else 0
        risk_percent = 100 * total_at_risk / total_value if total_value > 0 else 0

        return render_template('accounts/accounts.html', 
            total_deposit=total_deposit,
            total_withdraw=total_withdraw,
            total_invested=total_invested,
            total_value=total_value,
            total_unrealized_pnl=total_unrealized_pnl,
            total_return=total_return,
            total_at_risk = total_at_risk,
            risk_percent=risk_percent,
            accounts=accounts
        )

    @app.route('/history/<account_id>')
    def route_history(account_id):
        account = exchange.get_account(account_id)
        history = cpbro_history.histories[account_id]
        transfers = cpbro_history.transfers[account_id]
        return render_template('accounts/history.html', account=account, history=history, transfers=transfers)

    @app.route('/orders')
    def route_orders():
        orders = sorted(cpbro_history.orders.values(), key=lambda x: x["created_at"], reverse=True)
        return render_template('accounts/orders.html', orders=orders)

    return app

def main():
    global logger

    args = parse_cli_args()
    logger = make_logger('cbpro-accoung-history', args.log_file)

    with open(args.config) as f:
        config = json.load(f)

    exchange = make_exchange(config["exchange"])
    history = CpbroHistory(exchange)

    if args.cache_file:
        history.load_from_cache(args.cache_file)

    update_all_accounts(exchange, history)
    
    app = make_flask_app(exchange, history)

    update_thread = CbproHistoryUpdateThread(exchange, history)
    update_thread.start()

    app.run(host='0.0.0.0', port=args.port, debug=True, threaded=True, use_reloader=False)

    update_thread.stop()
    update_thread.join()

main()