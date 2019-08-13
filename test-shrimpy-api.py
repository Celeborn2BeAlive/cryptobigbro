import argparse, os, logging, json
import shrimpy

def parse_cli_args():
    def parse_string_list(string):
        return string.split(',')

    parser = argparse.ArgumentParser(description='Desc')
    parser.add_argument('-l', '--log-file', help='Path to log file.')

    parser.add_argument("credential_file", help='Path to a json file containing credentials for the API')

    return parser.parse_args(), parser

def init_logging(log_file=None):
    if log_file:
        if os.path.splitext(log_file)[1] == '.html':
            logging.basicConfig(filename=log_file, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s<br>', level=logging.INFO)
        else:
            logging.basicConfig(filename=log_file, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
        logging.info(f'Logging to file {log_file}')
    else:
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
        logging.info('Logging to standard output')

def main():
    args, args_parser = parse_cli_args()

    init_logging(args.log_file)
  
    with open(args.credential_file) as f:
        credentials = json.load(f)
    
    client = shrimpy.ShrimpyApiClient(credentials['apiKey'], credentials['apiSecret'])
    print(client.get_ticker('coinbasepro'))

if __name__ == "__main__":
    main()