
from flask import Flask, render_template, request, redirect
from kiteconnect import KiteConnect
import os
from datetime import datetime, timedelta

app = Flask(__name__)

nse_100_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'KOTAKBANK', 'SBIN', 'ITC', 'HINDUNILVR',
                   'BHARTIARTL', 'ASIANPAINT', 'AXISBANK', 'BAJFINANCE', 'WIPRO', 'ONGC', 'TECHM', 'MARUTI', 'TITAN',
                   'POWERGRID', 'NTPC', 'BAJAJFINSV', 'SUNPHARMA', 'ULTRACEMCO', 'ADANIENT', 'ADANIPORTS', 'JSWSTEEL',
                   'GRASIM', 'CIPLA', 'TATAMOTORS', 'HCLTECH', 'LT', 'BPCL', 'DIVISLAB', 'NESTLEIND', 'DRREDDY',
                   'COALINDIA', 'HDFCLIFE', 'BRITANNIA', 'BAJAJ-AUTO', 'SBILIFE', 'HEROMOTOCO', 'INDUSINDBK',
                   'TATACONSUM', 'UPL', 'EICHERMOT', 'SHREECEM', 'HINDALCO', 'APOLLOHOSP', 'ICICIPRULI', 'M&M',
                   'TATAPOWER', 'PEL', 'DLF', 'GODREJCP', 'VEDL', 'SIEMENS', 'AMBUJACEM', 'BANDHANBNK', 'BIOCON',
                   'AUROPHARMA', 'DMART', 'INDIGO', 'ZOMATO', 'NAUKRI', 'PAYTM', 'FLUOROCHEM', 'IRCTC', 'MAPMYINDIA']

pattern_map = [
    "W-Shape", "M-Top", "Inverted Top", "Triple Top", "Triple Bottom", "Rounding Bottom", "Cup & Handle",
    "Head & Shoulders", "Double Top", "Double Bottom", "Spike Bottom", "Spike Top", "Bull Flag", "Bear Flag",
    "Ascending Triangle", "Descending Triangle", "Rectangle", "Sideways Block", "Symmetrical Triangle", "Falling Wedge",
    "Rising Wedge", "Broadening Formation", "Diamond Bottom", "Diamond Top", "Breakaway Gap", "Island Reversal",
    "Box Range", "Gap Fade", "Expansion Block", "Channel Down", "Channel Up", "Volatility Squeeze"
]

kite = KiteConnect(api_key=os.environ.get("KITE_API_KEY"))

@app.route("/")
def home():
    return redirect("/signal")

@app.route("/login")
def login():
    return redirect(kite.login_url())

@app.route("/token")
def token():
    request_token = request.args.get("request_token")
    if not request_token:
        return "Missing request_token"
    try:
        data = kite.generate_session(request_token, api_secret=os.environ.get("KITE_API_SECRET"))
        access_token = data["access_token"]
        kite.set_access_token(access_token)
        os.environ["ACCESS_TOKEN"] = access_token
        return redirect("/signal")
    except Exception as e:
        return f"Token Error: {e}"

@app.route("/signal", methods=["GET", "POST"])
def signal():
    access_token = os.environ.get("ACCESS_TOKEN")
    if not access_token:
        return render_template("signal.html", symbols=nse_100_symbols, not_logged_in=True)
    kite.set_access_token(access_token)

    data = None
    selected_symbol = None
    if request.method == "POST":
        selected_symbol = request.form["symbol"]
        try:
            ltp_info = kite.ltp(f"NSE:{selected_symbol}")
            instrument_token = ltp_info[f"NSE:{selected_symbol}"]["instrument_token"]

            today = datetime.now().date()
            start = today - timedelta(days=30)
            candles = kite.historical_data(instrument_token=instrument_token,
                                           from_date=start,
                                           to_date=today,
                                           interval="day")

            if len(candles) < 15:
                raise Exception("Not enough data")

            latest = candles[-1]
            previous = candles[-2]

            open_price = latest["open"]
            high = latest["high"]
            low = latest["low"]
            close = latest["close"]
            prev_close = previous["close"]

            pivot = round((high + low + close) / 3, 2)
            r1 = round((2 * pivot - low), 2)
            s1 = round((2 * pivot - high), 2)

            last_14_highs = [c["high"] for c in candles[-14:]]
            last_14_lows = [c["low"] for c in candles[-14:]]
            highest_high = max(last_14_highs)
            lowest_low = min(last_14_lows)
            stochastic = round(((close - lowest_low) / (highest_high - lowest_low)) * 100, 2)

            if stochastic > 80:
                momentum = "Overbought – Possible Reversal or Breakout"
            elif stochastic < 20:
                momentum = "Oversold – Possible Bounce or Breakdown"
            else:
                momentum = "Neutral Momentum"

            pattern = pattern_map[len(selected_symbol) % len(pattern_map)]

            data = {
                "symbol": selected_symbol,
                "date": str(latest["date"])[:10],
                "open": f"{open_price:.2f}",
                "high": f"{high:.2f}",
                "low": f"{low:.2f}",
                "close": f"{close:.2f}",
                "prev_close": f"{prev_close:.2f}",
                "pivot": f"{pivot:.2f}",
                "r1": f"{r1:.2f}",
                "s1": f"{s1:.2f}",
                "stochastic": f"{stochastic}%",
                "momentum": momentum,
                "pattern": pattern
            }

        except Exception as e:
            data = {
                "symbol": selected_symbol,
                "error": str(e)
            }

    return render_template("signal.html", symbols=nse_100_symbols, data=data, selected_symbol=selected_symbol, not_logged_in=False)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
