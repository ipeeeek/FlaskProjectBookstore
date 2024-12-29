from config import Config
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Book

app = Flask(__name__, template_folder='templates') # Important for template finding
app.config.from_object(Config)

engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
