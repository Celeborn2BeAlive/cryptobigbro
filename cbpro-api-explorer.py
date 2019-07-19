import argparse, json, os
from flask import Flask, render_template, request
from pprint import pprint, pformat
from exchanges import make_exchange

def parse_cli_args():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('config', type=str, help='Path to a json configuration file')
    parser.add_argument('-p', '--port', type=int, default=5000, help='Port for the web interface/API')

    return parser.parse_args()

def make_flask_app(exchange):
    app = Flask(__name__)

    @app.route('/')
    def main_route():
        return render_template('cbpro-api-explorer/index.html')

    @app.route('/<path:path>')
    def get_route(path):
        result = exchange.api_request('get', '/' + path)
        return pformat(result, indent=4)

    @app.route('/request', methods=['POST'])
    def post_route():
        print(request.form['url'])
        try:
            params = json.loads(request.form['params'])
            print(params)
        except Exception as e:
            print(e)
            params = {}
        result = exchange.api_request('post', '/' + request.form['url'], params)
        return pformat(result, indent=4)
    
    return app

def main():
    args = parse_cli_args()

    with open(args.config) as f:
        config = json.load(f)
    
    exchange = make_exchange(config["exchange"])

    app = make_flask_app(exchange)
    app.run(host='0.0.0.0', port=args.port, debug=True, threaded=True, use_reloader=False)

main()