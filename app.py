from random import uniform
from flask import Flask, render_template, request, abort
from flask_pymongo import PyMongo
from requests import get
import pandas as pd
import auth

API_VERSION = "/api/v1.0"
ENNY_URL = "https://enny.azurewebsites.net"

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://db:27017/market"
mongo = PyMongo(app)
db = mongo.db
users = db["users"]


@auth.authorize
@app.route(f"{API_VERSION}/<symbol>/sell", methods=["POST"])
def sell_stock(symbol):
    """Check the price of a stock, remove correct amounts of stock in 
    users portfolio. Add correct amount of value tokens AKA money 
    to users account."""
    uid = request.headers.get("uid")
    amount = int(request.json["amount"])
    price_per_share = get_stock_price(symbol)
    total_transaction = price_per_share * amount
    try:
        if uid:
            user = get_user(uid)
            portfolio = user["portfolio"]
            if not portfolio.get(symbol):
                portfolio[symbol] = 0
            if float(portfolio.get(symbol)) > amount:
                portfolio[symbol] = float(portfolio[symbol]) - amount
                users.update_one(
                    {"uid": user["uid"]},
                    {
                        "$set": {
                            "balance": float(user["balance"]) + total_transaction,
                            "portfolio": portfolio,
                        }
                    },
                )
                return get_user(uid)
            else:
                return {"message": "Not enough stocks for that transaction"}
        else:
            abort(403)
    except TypeError:
        abort(404)


@auth.authorize
@app.route(f"{API_VERSION}/<symbol>/buy", methods=["POST"])
def buy_stock(symbol):
    """Check the price of a stock, place correct amounts of stock in 
    users portfolio. Remove correct amount of value tokens AKA money 
    from users account."""
    uid = request.headers.get("uid")
    amount = int(request.json["amount"])
    price_per_share = get_stock_price(symbol)
    total_transaction = price_per_share * amount
    if uid:
        user = get_user(uid)
        portfolio = user["portfolio"]
        if not portfolio.get(symbol):
            portfolio[symbol] = 0
        if float(user["balance"]) > total_transaction:
            portfolio[symbol] = float(portfolio[symbol]) + amount
            users.update_one(
                {"uid": user["uid"]},
                {
                    "$set": {
                        "balance": float(user["balance"]) - total_transaction,
                        "portfolio": portfolio,
                    }
                },
            )
            return get_user(uid)
        else:
            return {"message": "Not enough money for that transaction"}
    else:
        abort(403)


@app.route(f"{API_VERSION}/signup", methods=["POST"])
def signup_user():
    return auth.signup_user()


@auth.authorize
@app.route(f"{API_VERSION}/user/info")
def get_user_info():
    uid = request.headers.get("uid")
    if uid:
        return get_user(uid)
    else:
        abort(403)


def get_user(uid):
    user = users.find_one_or_404({"uid": uid})
    user.pop("_id")
    return user


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
