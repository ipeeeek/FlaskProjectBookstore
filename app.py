from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from sqlalchemy import text

# Create an instance of Flask
app = Flask(__name__)

# Load configuration
app.config.from_object(Config)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Test the connection (Optional but recommended)
try:
    # Use text() to wrap the SQL query
    with app.app_context():
        result = db.session.execute(text('SELECT 1'))
        print("Database connected successfully")
except Exception as e:
    print(f"Database connection error: {e}")
