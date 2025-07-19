
from flask import Flask, render_template, redirect, request, url_for
from kiteconnect import KiteConnect
import os

app = Flask(__name__)

# Set your API key and secret from environment
api_key = os.environ.get("KITE_API_KEY")
api_secret = os.environ.get("KITE_API_SECRET")
kite = KiteConnect(api_key=api_key)

symbols = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "KOTAKBANK",
    "SBIN", "ITC", "HINDUNILVR", "BHARTIARTL", "ASIANPAINT", "AXISBANK",
    "BAJFINANCE", "WIPRO", "ONGC", "TECHM", "MARUTI", "TITAN", "POWERGRID",
    "NTPC", "BAJAJFINSV", "SUNPHARMA", "ULTRACEMCO", "ADANIENT", "ADANIPORTS"
]

@app.route("/login")
def login():
    login_url = kite.login_url()
    return redirect(login_url)

@app.route("/token")
def token():
    request_token = request.args.get("request_token")
    if not request_token:
        return "Request token missing", 400
    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        os.environ["ACCESS_TOKEN"] = access_token
        return redirect(url_for("strategy"))
    except Exception as e:
        return f"Error generating access token: {e}"

@app.route("/", methods=["GET", "POST"])
def strategy():
    symbol = None
    quantity = None
    action = None
    margin = None
    required = None
    status = None
    repeat = None

    access_token = os.environ.get("ACCESS_TOKEN")
    if not access_token:
        return redirect(url_for("login"))

    kite.set_access_token(access_token)

    if request.method == "POST":
        symbol = request.form["symbol"]
        quantity = int(request.form["quantity"])
        repeat = int(request.form["repeat"])

        try:
            quote = kite.quote(f"NSE:{symbol}")
            price = quote[f"NSE:{symbol}"]["last_price"]
            margin = 50000  # dummy margin
            required = price * quantity
            action = "Buy" if price % 2 == 0 else "Sell"
            status = "Sufficient Margin" if margin >= required else "Insufficient Margin"
        except Exception as e:
            action = "Error"
            status = str(e)
            price = 0
            margin = 0
            required = 0

    return render_template("trade.html",
        symbols=symbols,
        selected_symbol=symbol,
        quantity=quantity,
        action=action,
        margin=margin,
        required=required,
        status=status,
        repeat=repeat
    )

if __name__ == "__main__":
    app.run(debug=True)
