import os

from flask import Flask, session, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import scoped_session, sessionmaker
import traceback
import hashlib


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")
#get GoodReads API key:
if not os.getenv("API_KEY"):
    raise RuntimeError("API_KEY is not set")
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
            session["logged_in"] = True
            return render_template("index.html")
    else:
        return render_template("index.html")


@app.route("/dashboard", methods=["POST"])
def dashboard():
    firstName = "User"

    if "user_info" in session and session["logged_in"] == True:
        firstName = session["user_info"]["firstName"]
        user_id = session["user_info"]["user_id"]
        userReviews = db.execute("SELECT reviews.*,books.title FROM reviews INNER JOIN books ON reviews.book_id=books.id WHERE reviews.user_id=:user_id",{"user_id": user_id}).fetchall()
        #session["user_info"] = {"user_id":user_id, "firstName":firstName, "reviews":userReviews}
        #session["user_info"]["reviews"] = userReviews
        return render_template("userPage.html", firstName=firstName, reviews=userReviews)
    else:
        username = str(request.form.get("username").upper())
        password = str(request.form.get("password"))
        passwordHash = hashlib.sha256() #idk why this cant be a global
        passwordHash.update(password.encode('utf8'))
        hashedPassword = str(passwordHash.hexdigest()) #I have no clue why I have to do this line
        if(db.execute("SELECT * FROM users WHERE upper(username) = :username AND password = :password", {"username": username, "password": hashedPassword}).rowcount == 1):
            session["logged_in"] = True
            user = db.execute("SELECT * FROM users WHERE upper(username) = :username AND password = :password", {
                "username": username, "password": hashedPassword}).fetchone()
            user_id = user.id
            firstName = (user.firstname).capitalize()
            session["user_info"] = {"user_id": user_id, "firstName": firstName}
            userReviews = db.execute("SELECT reviews.*,books.title FROM reviews INNER JOIN books ON reviews.book_id=books.id WHERE reviews.user_id=:user_id",{"user_id": user_id}).fetchall()
            return render_template("userPage.html", firstName=firstName, reviews=userReviews)

        else:
            errorMessage = "username or password is incorrect"
            return render_template("error.html", error=errorMessage)


@app.route("/signUp")
def signUp():
    return render_template("signUp.html")


@app.route("/userCreationComplete", methods=["POST"])
def userCreationComplete():
    firstName = str(request.form.get("firstName"))
    lastName = str(request.form.get("lastName"))
    email = str(request.form.get("email"))
    username = str(request.form.get("username").upper())
    password = str(request.form.get("password"))
    passwordHash = hashlib.sha256()
    passwordHash.update(password.encode('utf8'))
    hashedPassword = str(passwordHash.hexdigest()) #I have no clue why I have to do this line
    if(len(password) < 8):
        errorMSG = "Password must be at least 8 characters long"
        return render_template("error.html", error = errorMSG)
    if(not firstName or not lastName or not email or not username or not password):
        return render_template("error.html")

    else:
        try:
            
            db.execute("INSERT INTO users (firstName, lastName, email, username, password) VALUES (:firstName, :lastName, :email, :username, :password)",
                       {"firstName": firstName, "lastName": lastName, "email": email, "username": username, "password": hashedPassword})
            db.commit()
        except Exception as error:
            errorMSG = error.args[0]
            return render_template("error.html", error=errorMSG)
        else:
            session["logged_in"] = True
            userInfo = db.execute("SELECT * FROM users WHERE username =:username",{"username":username}).fetchone()
            session["user_info"] = {"user_id": userInfo.id, "firstName": userInfo.firstname}
            return render_template("userCreationComplete.html")

@app.route("/logout")
def logout():
    session["logged_in"] = False
    message = "Please close tab to finish logging out!"
    session.clear()
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
    #reviews = db.execute("SELECT reviews.* FROM reviews WHERE book_id =:book_id", {"book_id": book.id}).fetchall()
    reviews = db.execute("SELECT reviews.*, books.id AS bookID, users.username FROM reviews INNER JOIN users ON reviews.user_id=users.id INNER JOIN books ON reviews.book_id=books.id WHERE book_id =:book_id",{"book_id": book.id}).fetchall()
    numberOfReviews = len(reviews)
    session["book_id"] = book.id
    user_id = session["user_info"]["user_id"]
    hasReviews = db.execute("SELECT reviews.*, books.id AS bookID, users.id FROM reviews INNER JOIN users ON reviews.user_id=users.id INNER JOIN books ON reviews.book_id=books.id WHERE user_id=:user_id AND book_id=:book_id",{"book_id":book.id, "user_id":user_id}).rowcount
    ratings = db.execute("SELECT rating FROM reviews WHERE book_id =:book_id",{"book_id":book.id}).fetchall()
    avgRating = None
    sumRatings = 0
    count = 0
    if ratings is None:
        avgRating = "No reviews yet"
    else:
        for rating in ratings:
            #this is the jankiest thing ive ever done
            sumRatings = sumRatings + rating.rating
            count = count + 1
        avgRating = float(sumRatings/count)
    canPost = False
    if not hasReviews:
        canPost = True
    else:
        canPost = False
    if request.method == "POST":
        
        goodReadsReviews = request.get("https://www.goodreads.com/book/review_counts.json", params={"key": "KEY", "isbns": "9781632168146"})
        session["book_id"] = book.id

        return render_template("reviewPage.html", book=book, reviews=reviews, canPost=canPost, avgRating = avgRating)
        
    if request.method == "GET":
        if book is None:
            return jsonify({"error": "No book with ISBN in database"}), 404
        else:
            return jsonify({
                "title": book.title,
                "author": book.author,
                "year": book.year,
                "isbn": book.isbn,
                "review_count":numberOfReviews,
                "average_score": avgRating
            })


@app.route("/review/confirm", methods=["POST"])
def confirm():
    rating = request.form.get("rating")
    review = request.form.get("review")
    book_id = session["book_id"]
    user_id = session["user_info"]["user_id"]
    try:
        db.execute("INSERT INTO reviews (user_id, book_id, review, rating) VALUES (:user_id, :book_id, :review, :rating)", {
                   "user_id": user_id, "book_id": book_id, "review": review, "rating": rating})
        db.commit()
        return render_template("success.html")
    except Exception as error:
        errorMSG = error.args[0]
        return render_template("error.html", error=errorMSG)
    # TODO: fix letter casing bugs in dashboard and review page
    # TODO: Get reviews from goodreads.com API
    # TODO: Fix front-end
    # TODO: Change from list of books to cards
    # --------COMPLETED--------
    # TODO: Add this stuff to the DB.. Somehow get the USER_ID and BOOK_ID to add this in the DB
    # TODO: Add confirm.html (and error?html) to tell user if DB was updated []
    # TODO: Add code to 'reviewPage.html' to display current reviews from DB []
    # TODO: remove case sensitivty in username
    # TODO: add password constraints in sign up
    # TODO: Add average review for each book