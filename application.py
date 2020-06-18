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
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

firstName = "user"
#session["logged_in"] = None


@app.route("/")
def index():
    if ("logged_in" in session):
        session["logged_in"] = False
        return render_template("index.html")
    if(session["logged_in"]):
        return render_template(dashboard())
    else:
        return render_template("index.html")


@app.route("/dashboard", methods=["POST"])
def dashboard():
    username = request.form.get("username")
    password = request.form.get("password")
    if(db.execute("SELECT * FROM users WHERE username = :username AND password = :password", {"username": username, "password": password}).rowcount == 1):
        session["logged_in"] = True
        firstName = db.execute("SELECT firstName FROM users WHERE username = :username AND password = :password", {
                               "username": username, "password": password}).fetchone()
        firstName = (firstName.firstname).capitalize()
        return render_template("userPage.html", firstName=firstName)
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
        if(db.execute("SELECT * FROM books WHERE upper(isbn) LIKE CONCAT('%', :isbn, '%')",{"isbn":query}).rowcount == 0):
            hasResults = False
        else:
            results = db.execute("SELECT * FROM books WHERE upper(isbn) LIKE CONCAT('%', :isbn, '%')",{"isbn":query}).fetchall()
            hasResults = True
        
    if(queryParameter == "author"):
        if(db.execute("SELECT * FROM books WHERE upper(author) LIKE CONCAT('%', :author, '%')", {"author":query}).rowcount == 0):
            hasResults = False
        else:
            results = db.execute("SELECT * FROM books WHERE upper(author) LIKE CONCAT('%', :author, '%')", {"author":query}).fetchall()
            hasResults = True
    if(queryParameter == "title"):
        if(db.execute("SELECT * FROM books WHERE upper(title) LIKE CONCAT('%', :title, '%')", {"title":query}).rowcount == 0):
            hasResults = False
        else:    
            results = db.execute("SELECT * FROM books WHERE upper(title) LIKE CONCAT('%', :title, '%')", {"title":query}).fetchall()
            hasResults = True
    return render_template("searchResult.html", results = results, hasResults = hasResults)
   

@app.route("/review/<string:isbn>", methods = ["POST","GET"])
def displayInfo(isbn):
    if request.method == "GET":
        book = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
        return jsonify({
            "isbn":book.isbn,
            "title":book.title,
            "author":book.author
        })
   
