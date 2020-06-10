from flask_pymongo import PyMongo
from flask import Flask, request, abort
from passlib.hash import pbkdf2_sha256
from passlib.pwd import genword
from functools import wraps
import string

API_VERSION = "/api/v1.0"
app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://db:27017"
mongo = PyMongo(app)
pws = mongo.cx["pwd"]
market_db = mongo.cx["market"]
hashes = pws["hashes"]
users = market_db["users"]


def signup_user():
    pwd = genword(length=16)
    uid = genword(length=8)
    hashes.insert_one(
        {"hash": pbkdf2_sha256.encrypt(pwd, rounds=2000, salt_size=16), "uid": uid}
    )
    new_user = {"uid": uid, "balance": "10000", "portfolio": {}}
    users.insert_one(new_user)
    return f"Registered! Set these headers on your requests to authenticate:\nuid: {uid}\nauthorization_key: {pwd}"


def get_uid(pwd):
    user = hashes.find_one(
        {"hash": pbkdf2_sha256.encrypt(pwd, rounds=2000, salt_size=16)}
    )
    return user["uid"]


def authorize(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        uid = request.headers.get("uid")
        key = request.headers.get("authorization_key")
        user = hashes.find_one_or_404({"uid": uid})
        if not uid and not key and not pbkdf2_sha256.verify(key, user["hash"]):
            abort(401)
        return f(*args, **kwargs)

    return wrapper
