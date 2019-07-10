import argparse, json
from flask import Flask, render_template
from pprint import pprint
from exchanges import make_exchange

def parse_cli_args():
    parser = argparse.ArgumentParser(description='Crypto Big Bro Coinbasepro Account History')
    
    parser.add_argument('config', type=str, help='Path to a json configuration file')
    parser.add_argument('-p', '--port', type=int, default=5000, help='Port for the web interface/API')
    parser.add_argument('-c', '--cache-file', type=str, help='Path to a file to store history')

    return parser.parse_args()

class CpbroHistory:
    def __init__(self, exchange):
        self.accounts = []
        self.update(exchange)
    
    def update(self, exchange):
        self.accounts = exchange.get_accounts()
        for a in self.accounts:
            a["history"] = exchange.get_account_history(a["id"])

def make_flask_app(exchange, history):
    app = Flask(__name__)

    @app.route('/')
    def route_index():
        accounts = [ a for a in exchange.get_accounts() if a['balance'] > 0.0 ]
        total_value = 0
        for a in accounts:
            a['value'] = a['balance'] * exchange.get_price(a['currency'], 'EUR') if a['currency'] != 'EUR' else a['balance']
            total_value += a['value']
        for a in accounts:
            a['percentage'] = 100.0 * a['value'] / total_value
        return render_template('investor/accounts.html', accounts=accounts)

    @app.route('/history/<account_id>')
    def route_history(account_id):
        account = exchange.get_account(account_id)
        history = exchange.get_account_history(account_id)
        return render_template('investor/history.html', account=account, history=history)

    return app

def main():
    args = parse_cli_args()

    with open(args.config) as f:
        config = json.load(f)
    
    pprint(config)

    exchange = make_exchange(config["exchange"])
    history = CpbroHistory(exchange)

    app = make_flask_app(exchange, history)

    app.run(host='0.0.0.0', port=args.port, debug=True, threaded=True, use_reloader=False)

main()