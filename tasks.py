from celery import Celery
from random import choices
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

    today = app.get_timestamp()["date"]
    symbols = choices(syms, k=30)
    for symbol in symbols:
        symbol = symbol.strip("\n") 
        if quant.moving_window(app.get_stock_history(symbol)):
            try:
                order = {
                    "stock": symbol,
                    "price": app.get_stock_price(symbol),
                    "amount": 200,
                    "limit": "2030-01-01",
                    "user": "UBUROI",
                }
                app.asks.insert_one(order)
                app.bids.insert_one(order)
            except NotFound:
                pass
        return "COOL MAN"
