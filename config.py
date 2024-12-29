#SQLAlchemy configurations
class Config:
    SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc://bookstore_dev_user:booksRus@localhost/bookstore_dev?driver=ODBC+Driver+17+for+SQL+Server'
    SQLALCHEMY_TRACK_MODIFICATIONS = False