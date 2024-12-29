import pyodbc

connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost,1433;"  # Use localhost or your server's IP address
    "DATABASE=bookstore_dev;"
    "UID=bookstore_dev_user;"
    "PWD=booksRus;"
    "TrustServerCertificate=yes"
)

try:
    conn = pyodbc.connect(connection_string)
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
