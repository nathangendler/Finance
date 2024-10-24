import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, change
from datetime import datetime


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    if "username" in session:
            username = session['username']

    stocks = db.execute("SELECT * FROM stocks WHERE username = ?", username)
    for stock in stocks:
        current_price1 = lookup(stock["ticker"])
        current_price = current_price1["price"]
        stock["username"] = current_price
    all_stocks = 0
    for stock in stocks:
        all_stocks += stock["username"] * stock["amount"]
    user_cash_list = db.execute("SELECT cash FROM users WHERE username = ?", username)
    user_cash = user_cash_list[0]["cash"]
    total = user_cash + all_stocks
    for stock in stocks:
        stock["username"] = usd(stock["username"])
    return render_template("index.html", stocks=stocks, all_stocks=usd(all_stocks), user_cash=usd(user_cash), total=usd(total))

@app.route("/history")
@login_required
def history():
    if "username" in session:
            username = session['username']

    transactions = db.execute("SELECT * FROM history WHERE username = ?", username)

    return render_template("history.html", transactions=transactions)





@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol")


        amount_of_shares = request.form.get("shares", type=int)

        if symbol == None or lookup(symbol) == None:
            return apology("ticker missing or invalid", 400)
        if not amount_of_shares or amount_of_shares == None:
            return apology("invalid amount of shares", 400)
        if "username" in session:
            username = session['username']

        symbol_dict = lookup(symbol)
        price = symbol_dict["price"]
        user_cash_list = db.execute("SELECT cash FROM users WHERE username = ?", username)
        user_cash = user_cash_list[0]["cash"]
        if (price*amount_of_shares) > user_cash:
            return apology("not enough funds", 0)

        user_cash -= price*amount_of_shares
        db.execute("UPDATE users SET cash = ? WHERE username = ?", user_cash, username)

        if db.execute("SELECT * from stocks where username = ? and ticker = ?", username, symbol):
            previous_amount1 = db.execute("SELECT amount FROM stocks WHERE username = ? and ticker = ?", username, symbol)
            previous_amount = previous_amount1[0]["amount"]
            new_amount = previous_amount + amount_of_shares
            db.execute("UPDATE stocks SET amount = ? WHERE username = ? and ticker = ?", new_amount, username, symbol)
        else:
            db.execute("INSERT INTO stocks (username, ticker, amount) VALUES(?, ?, ?)", username, symbol, amount_of_shares)
        x = "buy"
        now = datetime.now()
        date_time = now.strftime("%d/%m/%Y %H:%M:%S")
        price1 = usd(price)
        db.execute("INSERT INTO history (username, ticker, price, amount, buy_or_sell, date_time) VALUES(?, ?, ?, ?, ?, ?)", username, symbol, price1, amount_of_shares, x, date_time)

        return redirect("/")
    else:
        return render_template("buy.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        symbol = request.form.get("symbol")

        sell_amount = request.form.get("shares", type=int)

        if symbol == None or lookup(symbol) == None:
            return apology("ticker missing or invalid", 400)
        if not sell_amount or sell_amount == None:
            return apology("invalid amount of shares", 400)

        if "username" in session:
            username = session['username']

        if db.execute("SELECT * from stocks where username = ? and ticker = ?", username, symbol):
            amount_owned_list = db.execute("SELECT amount FROM stocks WHERE username = ? and ticker = ?", username, symbol)
            amount_owned = amount_owned_list[0]["amount"]
            if sell_amount > amount_owned:
                return apology("not enough stocks owned", 400)
        else:
            return apology("not enough stocks owned", 400)


        symbol_dict = lookup(symbol)
        price = symbol_dict["price"]

        user_cash_list = db.execute("SELECT cash FROM users WHERE username = ?", username)
        user_cash = user_cash_list[0]["cash"]

        user_cash += price*sell_amount
        db.execute("UPDATE users SET cash = ? WHERE username = ?", user_cash, username)

        if sell_amount == amount_owned:
            db.execute("DELETE FROM stocks WHERE username = ? and ticker = ?", username, symbol)
        else:
            amount_owned -= sell_amount
            db.execute("UPDATE stocks SET amount = ? WHERE username = ? and ticker = ?", amount_owned, username, symbol)
        x = "sell"
        now = datetime.now()
        date_time = now.strftime("%d/%m/%Y %H:%M:%S")
        price1 = usd(price)
        db.execute("INSERT INTO history (username, ticker, price, amount, buy_or_sell, date_time) VALUES(?, ?, ?, ?, ?, ?)", username, symbol, price1, sell_amount, x, date_time)
        return redirect("/")
    else:
        return render_template("sell.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["username"] = request.form.get("username")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        chart = db.execute("SELECT * FROM users")
        return render_template("login.html", chart=chart)


@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    if request.method == "POST":

        #checks for mistakes
        unique = True
        usernames = db.execute("SELECT username FROM users")
        for username in usernames:
            if request.form.get("username") == username["username"]:
                unique = False
        if not request.form.get("username"):
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        elif not request.form.get("confirmation"):
            return apology("must provide confirmation", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("password and confirmation do not match", 400)
        elif unique == False:
            return apology("username already in use", 400)
        else:
            x = generate_password_hash(request.form.get("password"))
            y = request.form.get("username")
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", y, x)

            return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("no ticker input", 400)
        symbol = request.form.get("symbol")
        stocks = lookup(symbol)
        if stocks == None:
            return apology("invalid ticker", 400)

        stocks["price"] = change(stocks["price"])
        stocks["week52High"] = change(stocks["week52High"])
        stocks["week52Low"] = change(stocks["week52Low"])
        return render_template("quoted.html", stocks=stocks)
    else:
        return render_template("quote.html")




