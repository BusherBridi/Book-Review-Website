import os

from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import scoped_session, sessionmaker
import traceback

import csv

# Set up database
engine = create_engine("postgres://qljlzzefwxpwox:477e86dbba51f73812c139efd2eacfc1f755e62fbc187d97d4a24613482d05f0@ec2-52-87-135-240.compute-1.amazonaws.com:5432/d9h58jebdkiikn")
db = scoped_session(sessionmaker(bind=engine))


f = open("books.csv")
reader = csv.reader(f)
for isbn, title, author, year in reader:
    db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)", {"isbn":isbn, "title":title, "author":author, "year":year})


db.commit()