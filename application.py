import os

from flask import Flask, session, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import scoped_session, sessionmaker
import traceback

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
# app.config["SESSION_PERMANENT"] = False
# app.config["SESSION_TYPE"] = "filesystem"
# Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

app.secret_key = "verysecretkey"


@app.route("/")
def index():
    if ("logged_in" in session):
        if(session["logged_in"] == True):
            return render_template("goToDashboard.html")
        else:
            return render_template("index.html")
    else:
        return render_template("index.html")


@app.route("/dashboard", methods=["POST"])
def dashboard():
    firstName = "User"
    
    if "user_info" in session and session["logged_in"] == True:
            firstName = session["user_info"]["firstName"]
            return render_template("userPage.html", firstName=firstName)
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        if(db.execute("SELECT * FROM users WHERE username = :username AND password = :password", {"username": username, "password": password}).rowcount == 1):
            session["logged_in"] = True
            user = db.execute("SELECT * FROM users WHERE username = :username AND password = :password", {
                                    "username": username, "password": password}).fetchone()
            user_id = user.id
            firstName = (user.firstname).capitalize()
            session["user_info"] = {"user_id":user_id, "firstName":firstName}
            return render_template("userPage.html", firstName = firstName)
            
        else:
            errorMessage = "username or password is incorrect"
            return render_template("error.html", error=errorMessage)


@app.route("/signUp")
def signUp():
    return render_template("signUp.html")


@app.route("/userCreationComplete", methods=["POST"])
def userCreationComplete():
    firstName = request.form.get("firstName")
    lastName = request.form.get("lastName")
    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")
    if(not firstName or not lastName or not email or not username or not password):
        return render_template("error.html")

    else:
        try:
            db.execute("INSERT INTO users (firstName, lastName, email, username, password) VALUES (:firstName, :lastName, :email, :username, :password)",
                       {"firstName": firstName, "lastName": lastName, "email": email, "username": username, "password": password})
            db.commit()
            return render_template("userCreationComplete.html")
        except Exception as error:
            errorMSG = error.args[0]
            return render_template("error.html", error=errorMSG)


@app.route("/logout")
def logout():
    session["logged_in"] = False
    message = "Please close tab to finish logging out!"
    return render_template("index.html", message=message)


@app.route("/searchResult", methods=["POST"])
def searchResult():
    query = request.form.get("query").upper()
    query = query.upper()
    queryParameter = request.form.get("searchGroup")
    results = None

    if(queryParameter == "isbn"):
        if(db.execute("SELECT * FROM books WHERE upper(isbn) LIKE CONCAT('%', :isbn, '%')", {"isbn": query}).rowcount == 0):
            hasResults = False
        else:
            results = db.execute(
                "SELECT * FROM books WHERE upper(isbn) LIKE CONCAT('%', :isbn, '%')", {"isbn": query}).fetchall()
            hasResults = True

    if(queryParameter == "author"):
        if(db.execute("SELECT * FROM books WHERE upper(author) LIKE CONCAT('%', :author, '%')", {"author": query}).rowcount == 0):
            hasResults = False
        else:
            results = db.execute(
                "SELECT * FROM books WHERE upper(author) LIKE CONCAT('%', :author, '%')", {"author": query}).fetchall()
            hasResults = True
    if(queryParameter == "title"):
        if(db.execute("SELECT * FROM books WHERE upper(title) LIKE CONCAT('%', :title, '%')", {"title": query}).rowcount == 0):
            hasResults = False
        else:
            results = db.execute(
                "SELECT * FROM books WHERE upper(title) LIKE CONCAT('%', :title, '%')", {"title": query}).fetchall()
            hasResults = True
    return render_template("searchResult.html", results=results, hasResults=hasResults)


@app.route("/review/<string:isbn>", methods=["POST", "GET"])
def displayInfo(isbn):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn",
                      {"isbn": isbn}).fetchone()
    session["book_id"] = book.id
    if request.method == "POST":
        session["book_id"] = book.id
        return render_template("reviewPage.html", book=book)
    if request.method == "GET":
        if book is None:
            return jsonify({"error": "No book with ISBN in database"}), 422
        else:
            return jsonify({
                "isbn": book.isbn,
                "title": book.title,
                "author": book.author
            })


@app.route("/review/confirm", methods=["POST"])
def confirm():
    rating = request.form.get("rating")
    review = request.form.get("review")
    book_id = session["book_id"]
    user_id = session["user_info"]["user_id"]
    try:
        db.execute("INSERT INTO reviews (user_id, book_id, review, rating) VALUES (:user_id, :book_id, :review, :rating)",{"user_id": user_id, "book_id": book_id, "review": review, "rating": rating})
        db.commit()
        return render_template("success.html")
    except Exception as error:
            errorMSG = error.args[0]
            return render_template("error.html", error=errorMSG)
    # TODO: Add this stuff to the DB.. Somehow get the USER_ID and BOOK_ID to add this in the DB
    # TODO: Add code to 'reviewPage.html' to display current reviews from DB
    # TODO: Add confirm.html (and error?html) to tell user if DB was updated
   
