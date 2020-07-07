import json
from random import uniform, choice
from flask import Flask, render_template, request, abort
from flask_pymongo import PyMongo
from requests import get
import pandas as pd
import tasks
import auth

API_VERSION = "/api/v1.0"
# ENNY_URL = "https://enny.azurewebsites.net"
ENNY_URL = "http://enny"

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://db:27017/market"
mongo = PyMongo(app)
db = mongo.db
users = db["users"]
bids = db["bids"]
asks = db["asks"]


@auth.authorize
@app.route(f"{API_VERSION}/broker/sell/<symbol>", methods=["POST", "GET"])
def place_ask(symbol):
    """Place an asking offer for a stock, check market for matching bids and either fulfil 
    the order of place it in the market. Checks incoming request for a json with 
    the amount of stock to sell, the asking price and the time limit. Returns status for the ask."""
    res = tasks.make_some_noise.delay()
    if request.method == "POST":
        if request.json:
            order = {
                "stock": symbol,
                "price": request.json["ask"],
                "amount": request.json["amount"],
                "limit": request.json["limit"],
                "user": request.headers.get("uid"),
            }
            try:
                query = {
                    "$and": [
                        {"stock": order["stock"]},
                        {"price": {"$lte": order["price"]}},
                        {"amount": {"$gte": order["amount"]}},
                        {"limit": {"$lte": get_timestamp()}},
                    ]
                }
                deal = asks.find_one(query)
                if deal:
                    return close(deal, order)
                else:
                    asks.insert_one(order)
                    return {
                        "msg": f"Your trade could not be fulfilled. Holding out until {order['limit']}"
                    }
            except Exception as e:
                return e
    else:
        everythong = []
        for r in bids.find({"stock": symbol}):
            r.pop("_id")
            everythong.append(r)
        return json.dumps(everythong)


@auth.authorize
@app.route(f"{API_VERSION}/broker/buy/<symbol>", methods=["POST", "GET"])
def place_bid(symbol):
    """Place a bid for a stock, check market for matching asks and either fulfil 
    the order of place it in the market. Checks incoming request for a json with 
    the amount of stock to buy, the bid and the time limit. Returns status for the bid."""
    res = tasks.make_some_noise.delay()
    if request.method == "POST":
        if request.json:
            order = {
                "stock": symbol,
                "price": request.json["bid"],
                "amount": request.json["amount"],
                "limit": request.json["limit"],
                "user": request.headers.get("uid"),
            }

            try:
                query = {
                    "$and": [
                        {"stock": order["stock"]},
                        {"price": {"$lte": order["price"]}},
                        {"amount": {"$gte": order["amount"]}},
                        {"limit": {"$lte": get_timestamp()}},
                    ]
                }
                deal = asks.find_one(query)
                if deal:
                    return close(deal, order)
                else:
                    bids.insert_one(order)
                    return {
                        "msg": f'Your trade could not be fulfilled. Holding out until {order["limit"]}'
                    }
            except Exception as e:
                return {"error": f"{str(e)}"}
    else:
        everythong = []
        for r in asks.find({"stock": symbol}):
            r.pop("_id")
            everythong.append(r)
        return json.dumps(everythong)


def reverse_number(number):
    return 0 - number


def close(ask, bid):
    transaction = bid["amount"] * ask["price"]
    buyer = get_user(bid["user"])
    seller = get_user(ask["user"])
    if not seller["uid"] == "UBUROI":
        if not seller.get("portfolio").get(bid["stock"]) >= bid["amount"]:
          asks.delete_one({"_id": ask["_id"]})
          return {
            "msg": f"Seller {seller['uid']} doesn't have the expected number of stock in their portfolio."
            }
    if float(buyer["balance"]) > transaction:
        change_balance(
            buyer, reverse_number(transaction), change_portfolio(buyer, bid)
        )
        if not seller["uid"] == "UBUROI":
            bid["amount"] = reverse_number(bid["amount"])
            change_balance(seller, transaction, change_portfolio(seller, bid))
        ask["amount"] = ask["amount"] - bid["amount"]
        if ask["amount"] > 0:
            asks.update_one(
                {"_id": ask["_id"]}, {"$set": {"amount": ask["amount"]}}
            )
        else:
            asks.delete_one({"_id": ask["_id"]})

    else:
        return {"msg": "Not enough money for that transaction."}
    return {
        "buyer": f"{get_user(bid['user'])}",
        "seller": f"{get_user(ask['user'])}",
    }


def change_portfolio(user, order):
    symbol = order["stock"]
    amount = order["amount"]
    portfolio = user["portfolio"]
    if not portfolio.get(symbol):
        portfolio[symbol] = 0
    portfolio[symbol] = float(portfolio[symbol]) + amount
    return portfolio


def change_balance(user, transaction, portfolio):
    tran = users.update_one(
        {"uid": user["uid"]},
        {
            "$set": {
                "balance": float(user["balance"]) + transaction,
                "portfolio": portfolio,
            }
        },
    )
    return tran.acknowledged


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
            change_balance(
                user,
                total_transaction,
                change_portfolio(user, {"stock": symbol, "amount": amount}),
            )
            return get_user(uid)
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
    total_transaction = float(price_per_share) * amount
    if uid:
        user = get_user(uid)
        portfolio = user["portfolio"]
        if not portfolio.get(symbol):
            portfolio[symbol] = 0
        if float(user["balance"]) > float(total_transaction):
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


def get_timestamp():
    """Make a call to the ticker to get current stock price, then 
    return an average daily price."""
    res = get(f"{ENNY_URL}/{API_VERSION}/timeline")
    if len(res.text) > 0:
        return json.loads(res.text)
    else:
        abort(404)


def get_stock_price(symbol):
    """Make a call to the ticker to get current stock price, then 
    return an average daily price."""
    res = get(f"{ENNY_URL}/{API_VERSION}/ticker/{symbol}/today")
    today = json.loads(res.text)
    if len(today) > 0:
        return uniform(today[0]["high"], today[0]["low"])
    elif today:
        return {"err": "Unable to get stock price"}
    else:
        abort(404)

def get_stock_history(symbol):
    res = get(f"{ENNY_URL}/{API_VERSION}/ticker/{symbol}")
    hist = json.dumps(res.json())
    return pd.read_json(hist)

if __name__ == "__main__":
    app.run()
