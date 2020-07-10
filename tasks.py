from celery import Celery
from random import choices
from datetime import datetime
from datetime import timedelta
from werkzeug.exceptions import NotFound

import app
import quant

celery = Celery(
    "tasks", broker="redis://redis:6379", result_backend="redis://redis:6378"
)


@celery.task()
def make_some_noise():
    with open("./NDX", "r") as stonks:
        syms = stonks.readlines()

    today = datetime.strptime(app.get_timestamp()["date"], "%Y-%m-%d")
    symbols = choices(syms, k=30)
    for symbol in symbols:
        symbol = symbol.strip("\n") 
        print(symbol)
        try:
            order = {
                "stock": symbol,
                "price": app.get_stock_price(symbol),
                "amount": 200,
                "limit": (today + timedelta(days = 5)).strftime("%Y-%m-%d"),
                "user": "UBUROI",
            }
            print(order)
        except NotFound:
            print("NOT FOUND")
            continue
        if quant.moving_window(app.get_stock_history(symbol)):
            app.bids.insert_one(order)
        else:
            app.asks.insert_one(order)
    return "COOL MAN"
