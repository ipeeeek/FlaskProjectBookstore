#SQLAlchemy configurations
import secrets

class Config:
    SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc://bookstore_dev_user:booksRus@localhost/bookstore_dev?driver=ODBC+Driver+17+for+SQL+Server'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = secrets.token_hex(16)
