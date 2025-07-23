from flask import Flask, redirect, request, jsonify, render_template
from kiteconnect import KiteConnect
import os
import datetime

app = Flask(__name__)

KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_API_SECRET = os.getenv("KITE_API_SECRET")
REDIRECT_URL = "https://smartdecisiontrader.onrender.com"

kite = KiteConnect(api_key=KITE_API_KEY)
kite_session = None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    login_url = kite.login_url()
    return redirect(login_url)

@app.route("/access_token")
def access_token():
    global kite_session
    request_token = request.args.get("request_token")
    data = kite.generate_session(request_token, api_secret=KITE_API_SECRET)
    kite.set_access_token(data["access_token"])
    kite_session = kite
    return "✅ Access token generated. You can now use /predict?symbol=RELIANCE"

@app.route("/predict")
def predict():
    try:
        symbol = request.args.get("symbol", "RELIANCE")
        instrument = f"NSE:{symbol.upper()}"
        to_date = datetime.datetime.now()
        from_date = to_date - datetime.timedelta(days=30)
        instrument_token = kite.ltp([instrument])[instrument]["instrument_token"]
        candles = kite_session.historical_data(
            instrument_token=instrument_token,
            from_date=from_date,
            to_date=to_date,
            interval="day"
        )
        if len(candles) < 14:
            return jsonify({ "error": "Not enough data." }), 400

        latest = candles[-1]
        prev = candles[-2]

        open_price = latest['open']
        high = latest['high']
        low = latest['low']
        close = latest['close']
        prev_close = prev['close']

        pivot = round((high + low + close) / 3, 2)
        r1 = round((2 * pivot - low), 2)
        s1 = round((2 * pivot - high), 2)

        highs = [c['high'] for c in candles[-14:]]
        lows = [c['low'] for c in candles[-14:]]
        highest_high = max(highs)
        lowest_low = min(lows)
        stochastic = round((close - lowest_low) / (highest_high - lowest_low) * 100, 2)

        momentum = "Neutral"
        if stochastic > 80:
            momentum = "Overbought – Possible Reversal"
        elif stochastic < 20:
            momentum = "Oversold – Possible Bounce"

        return jsonify({
            "symbol": symbol,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "prev_close": prev_close,
            "pivot": pivot,
            "r1": r1,
            "s1": s1,
            "stochastic": stochastic,
            "momentum": momentum
        })
    except Exception as e:
        return jsonify({ "error": str(e) }), 500

if __name__ == "__main__":
    app.run(debug=True)
