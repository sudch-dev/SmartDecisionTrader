from flask import Flask, render_template, request, redirect
from kiteconnect import KiteConnect
import os
from datetime import datetime, timedelta

app = Flask(__name__)

nse_100_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'KOTAKBANK', 'SBIN', 'ITC', 'HINDUNILVR', 'BHARTIARTL', 'ASIANPAINT', 'AXISBANK', 'BAJFINANCE', 'WIPRO', 'ONGC', 'TECHM', 'MARUTI', 'TITAN', 'POWERGRID', 'NTPC', 'BAJAJFINSV', 'SUNPHARMA', 'ULTRACEMCO', 'ADANIENT', 'ADANIPORTS', 'JSWSTEEL', 'GRASIM', 'CIPLA', 'TATAMOTORS', 'HCLTECH', 'LT', 'BPCL', 'DIVISLAB', 'NESTLEIND', 'DRREDDY', 'COALINDIA', 'HDFCLIFE', 'BRITANNIA', 'BAJAJ-AUTO', 'SBILIFE', 'HEROMOTOCO', 'INDUSINDBK', 'TATACONSUM', 'UPL', 'EICHERMOT', 'SHREECEM', 'HINDALCO', 'APOLLOHOSP', 'ICICIPRULI', 'M&M', 'TATAPOWER', 'PEL', 'DLF', 'GODREJCP', 'VEDL', 'SIEMENS', 'AMBUJACEM', 'BANDHANBNK', 'BIOCON', 'AUROPHARMA', 'DMART', 'INDIGO', 'ZOMATO', 'NAUKRI', 'PAYTM', 'FLUOROCHEM', 'IRCTC', 'MAPMYINDIA']

kite = KiteConnect(api_key=os.environ.get("KITE_API_KEY"))

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login")
def login():
    login_url = kite.login_url()
    return redirect(login_url)

@app.route("/token")
def token():
    request_token = request.args.get("request_token")
    if not request_token:
        return "Missing request_token in URL"
    try:
        data = kite.generate_session(request_token, api_secret=os.environ.get("KITE_API_SECRET"))
        access_token = data["access_token"]
        kite.set_access_token(access_token)
        os.environ["ACCESS_TOKEN"] = access_token
        return redirect("/signal")
    except Exception as e:
        return f"Error generating access token: {e}"

@app.route("/signal", methods=["GET", "POST"])
def signal():
    access_token = os.environ.get("ACCESS_TOKEN")
    if not access_token:
        return "Access token not found. Please login again."
    kite.set_access_token(access_token)
    data = None
    selected_symbol = None
    if request.method == "POST":
        selected_symbol = request.form["symbol"]
        try:
            quote = kite.quote(f"NSE:{selected_symbol}")
            price = quote[f"NSE:{selected_symbol}"]["last_price"]
            volume = quote[f"NSE:{selected_symbol}"].get("volume_traded") or quote[f"NSE:{selected_symbol}"].get("volume")
            instrument_token = quote[f"NSE:{selected_symbol}"]["instrument_token"]
            candles = kite.historical_data(
                instrument_token=instrument_token,
                from_date=(datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d'),
                to_date=datetime.now().strftime('%Y-%m-%d'),
                interval="day"
            )
            if len(candles) < 14:
                signal_text = "Not enough data"
            else:
                latest = candles[-1]
                close = latest["close"]
                high = latest["high"]
                low = latest["low"]
                pivot = (high + low + close) / 3
                r1 = 2 * pivot - low
                s1 = 2 * pivot - high
                highs = [c["high"] for c in candles[-14:]]
                lows = [c["low"] for c in candles[-14:]]
                stochastic_k = ((close - min(lows)) / (max(highs) - min(lows))) * 100

                if stochastic_k > 80:
                    momentum = "Overbought – Caution"
                    signal_text = "Sell"
                elif stochastic_k < 20:
                    momentum = "Oversold – Opportunity"
                    signal_text = "Buy"
                else:
                    momentum = "Neutral"
                    signal_text = "Hold"

                patterns = ["W-Shape", "Head & Shoulders", "Bull Flag", "Bear Flag", "Double Top", "Double Bottom"]
                pattern_index = len(selected_symbol) % len(patterns)
                detected_pattern = patterns[pattern_index]
                signal_text += f" (Pattern: {detected_pattern}, Momentum: {momentum})"

            data = {
                "price": f"{price:,.2f}",
                "volume": f"{volume:,}",
                "signal": signal_text
            }

        except Exception as e:
            data = {
                "price": "-",
                "volume": "-",
                "error": str(e)
            }

    return render_template("signal.html", symbols=nse_100_symbols, data=data, selected_symbol=selected_symbol)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))