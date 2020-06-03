from random import uniform
from flask import Flask, render_template, request, abort
from flask_pymongo import PyMongo
from requests import get
import pandas as pd

API_VERSION = "/api/v1.0"
ENNY_URL = "https://enny.azurewebsites.net"

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://db:27017/market"
mongo = PyMongo(app)
db = mongo.db
users = db["users"]


@app.route(f"{API_VERSION}/<symbol>/buy", methods=["POST"])
def buy_stock(symbol):
    """Check the price of a stock, place correct amounts of stock in 
    users portfolio. Remove correct amount of value tokens AKA money 
    from users account."""
    client_id = request.headers.get("client_id")
    amount = int(request.json["amount"])
    price_per_share = get_stock_price(symbol)
    total_transaction = price_per_share * amount
    if client_id:
        user = get_user(client_id)
        portfolio = user["portfolio"]
        if float(user["balance"]) > total_transaction:
            portfolio[symbol] = float(portfolio[symbol]) + amount
            users.update_one(
                {"client_id": user["client_id"]},
                {
                    "$set": {
                        "balance": float(user["balance"]) - total_transaction,
                        "portfolio": portfolio,
                    }
                },
            )
            return get_user(client_id)["portfolio"]
    else:
        abort(403)


def get_user(client_id):
    return users.find_one_or_404({"client_id": request.headers["client_id"]})


def get_stock_price(symbol):
    """Make a call to the ticker to get current stock price, then 
    return an average daily price."""
    res = get(f"{ENNY_URL}/{API_VERSION}/ticker/{symbol}/today")
    if len(res.text) > 0:
        df = pd.read_json(res.text)
        return uniform(df.tail(1).high.iat[0], df.tail(1).low.iat[0])
    else:
        abort(404)


if __name__ == "__main__":
    app.run()
