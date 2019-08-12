import argparse, time
import pandas as pd
from datetime import datetime, timezone, timedelta
from bokeh.plotting import figure, show, output_file
import dateparser

def parse_cli_args():
    parser = argparse.ArgumentParser(description='Plot an input csv file containing OHLCV data to an html document.')

    parser.add_argument("csv_file", type=str, help="Path to CSV file to plot.")
    parser.add_argument("-o", "--output-file", type=str, help="Path to output html file.")
    parser.add_argument("--start", help="Start date")
    parser.add_argument("--end", help="End date")

    return parser.parse_args()

def main():
    args = parse_cli_args()

    start_dt = datetime.utcfromtimestamp(0)
    if args.start:
        start_dt = dateparser.parse(args.start, settings={'TIMEZONE': 'UTC'})

    end_dt = datetime.utcfromtimestamp(time.time())
    if args.end:
        end_dt = dateparser.parse(args.end, settings={'TIMEZONE': 'UTC'})

    df = pd.read_csv(args.csv_file)
    w = (df["open_timestamp_utc"][1] - df["open_timestamp_utc"][0]) * 1000 * 0.5 # width of a bar: half the candle bar

    df["date"] = df["open_timestamp_utc"].map(lambda x: datetime.utcfromtimestamp(x))
 
    df = df[(start_dt <= df.date) & (df.date <= end_dt)]

    inc = df.close > df.open
    dec = df.open > df.close

    TOOLS = "pan,wheel_zoom,box_zoom,reset,save,crosshair"

    p = figure(x_axis_type="datetime", tools=TOOLS, plot_width=1000, title="OHLCV", output_backend="webgl")

    p.grid.grid_line_alpha=0.3

    p.segment(df.date, df.high, df.date, df.low, color="black")
    p.vbar(df.date[inc], w, df.open[inc], df.close[inc], fill_color="#D5E1DD", line_color="black")
    p.vbar(df.date[dec], w, df.open[dec], df.close[dec], fill_color="#F2583E", line_color="black")

    if args.output_file:
        output_file(args.output_file, title="OHLCV")

    show(p)

    return

if __name__ == "__main__":
    main()