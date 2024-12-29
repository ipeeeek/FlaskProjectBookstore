from flask import render_template
from app import app, Session # Import app and Session directly

from models import Book # Import Book directly

@app.route("/")
def index():
    session = Session()
    books = session.query(Book).limit(10).all()
    session.close()
    return render_template("index.html", books=books)

# ... other routes