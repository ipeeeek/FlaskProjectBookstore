from config import Config
from flask import Flask, render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Book  # Import your models

app = Flask(__name__)

# Load configuration from config.py before using it
app.config.from_object(Config)

# ... rest of your code using app.config values

engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

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