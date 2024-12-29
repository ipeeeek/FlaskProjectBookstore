from flask import Flask, render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Book  # Import your models

app = Flask(__name__)

# Database Configuration (replace with your credentials)
DATABASE_URI = "mssql+pyodbc://bookstore_dev_user:booksRus@localhost/bookstore_dev?driver=ODBC+Driver+17+for+SQL+Server"
engine = create_engine(DATABASE_URI)

# Create tables if they don't exist (important for initial setup)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

@app.route("/")
def index():
    session = Session()
    books = session.query(Book).limit(10).all()  # Get some books from the database
    session.close()
    return render_template("index.html", books=books)

if __name__ == "__main__":
    app.run(debug=True)  # debug=True for development