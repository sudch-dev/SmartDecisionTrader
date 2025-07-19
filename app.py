
from flask import Flask, render_template, request, redirect
from kiteconnect import KiteConnect
import os

app = Flask(__name__)
kite = KiteConnect(api_key=os.environ.get("KITE_API_KEY"))

nse_100 = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "ITC", "HINDUNILVR",
    "AXISBANK", "BAJFINANCE", "WIPRO", "ONGC", "TECHM", "MARUTI", "TITAN", "POWERGRID",
    "NTPC", "BAJAJFINSV", "SUNPHARMA", "ULTRACEMCO", "ADANIENT", "ADANIPORTS", "LT",
    "JSWSTEEL", "COALINDIA", "GRASIM", "TATAMOTORS", "BPCL", "EICHERMOT", "CIPLA"
]

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login")
def login():
    return redirect(kite.login_url())

@app.route("/token")
def token():
    request_token = request.args.get("request_token")
    try:
        data = kite.generate_session(request_token, api_secret=os.environ.get("KITE_API_SECRET"))
        kite.set_access_token(data["access_token"])
        os.environ["ACCESS_TOKEN"] = data["access_token"]
        return redirect("/trade")
    except Exception as e:
        return f"Error: {e}"

@app.route("/trade", methods=["GET", "POST"])
def trade():
    kite.set_access_token(os.environ.get("ACCESS_TOKEN"))
    message = None
    if request.method == "POST":
        symbol = request.form["symbol"]
        quantity = int(request.form["quantity"])
        repeat = int(request.form["repeat"])

        try:
            quote = kite.quote(f"NSE:{symbol}")
            ltp = quote[f"NSE:{symbol}"]["last_price"]
            volume = quote[f"NSE:{symbol}"]["volume_traded"] or quote[f"NSE:{symbol}"]["volume"]
            day_high = quote[f"NSE:{symbol}"]["ohlc"]["high"]
            day_low = quote[f"NSE:{symbol}"]["ohlc"]["low"]

            margin = kite.margins()["equity"]["net"]
            required = ltp * quantity
            status = "Sufficient" if margin >= required else f"Shortfall: ₹{required - margin:,.2f}"

            avg_trade_value = ltp * volume
            # Strategy logic
            if (ltp - day_low) / ltp < 0.005 and avg_trade_value > 5e7:
                signal = "Buy"
            elif (day_high - ltp) / ltp < 0.005 and avg_trade_value > 5e7:
                signal = "Sell"
            else:
                signal = "Hold"

            message = {
                "symbol": symbol,
                "quantity": quantity,
                "ltp": f"{ltp:,.2f}",
                "volume": f"{volume:,}",
                "day_high": f"{day_high:,.2f}",
                "day_low": f"{day_low:,.2f}",
                "margin": f"{margin:,.2f}",
                "required": f"{required:,.2f}",
                "status": status,
                "signal": signal,
                "repeat": repeat
            }

        except Exception as e:
            message = {"error": str(e)}

    return render_template("trade.html", symbols=nse_100, message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
