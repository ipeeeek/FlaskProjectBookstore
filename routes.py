from flask import request, render_template, session as flask_session, redirect, url_for, flash
from app import app, Session
from sqlalchemy import or_, text, exc
from sqlalchemy.exc import SQLAlchemyError
from utils import hash_password
from models import Book, Customer


@app.route("/")
def index():
    db_session = Session()  # Renaming session to db_session
    books = db_session.query(Book).limit(10).all()
    db_session.close()
    return render_template("index.html", books=books)


@app.route("/book/<int:book_id>")
def book_detail(book_id):
    db_session = Session()  # Renaming session to db_session
    book = db_session.query(Book).get(book_id)
    db_session.close()
    if book is None:
        return "Book not found", 404
    return render_template("book.html", book=book)


@app.route("/search")
def search():
    query = request.args.get("q")
    search_results = []

    if query:
        db_session = Session()  # Renaming session to db_session
        search_results = db_session.query(Book).filter(
            or_(
                Book.title.like(f"%{query}%"),
            )
        ).all()
        db_session.close()

    return render_template("index.html", books=search_results, query=query)

@app.route("/cart")
def view_cart():
    cart_items = []
    total_price = 0
    if "cart" in flask_session:
        db_session = Session()  # Renaming session to db_session
        for book_id, quantity in flask_session["cart"].items():
            book = db_session.query(Book).get(book_id)
            if book:
                cart_items.append({"book": book, "quantity": quantity})
                total_price += book.price * quantity
        db_session.close()

    return render_template("cart.html", cart_items=cart_items, total_price=total_price)


@app.route("/remove_from_cart/<int:book_id>")
def remove_from_cart(book_id):
    if "cart" in flask_session and book_id in flask_session["cart"]:
        del flask_session["cart"][book_id]
        flask_session.modified = True
    return redirect(url_for("cart"))


@app.route("/process_order", methods=["POST"])
def process_order():
    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        shipping_address_id = request.form.get("shipping_address_id")
        order_status_id = request.form.get("order_status_id")
        payment_id = request.form.get("payment_id")
        total_amount = request.form.get("total_amount")

        db_session = Session()  # Renaming session to db_session
        try:
            order_id_result = db_session.execute(text(
                "EXEC usp_process_order :customer_id, :shipping_address_id, :order_status_id, :payment_id, :total_amount, @order_id OUTPUT"
            ), {
                "customer_id": customer_id,
                "shipping_address_id": shipping_address_id,
                "order_status_id": order_status_id,
                "payment_id": payment_id,
                "total_amount": total_amount
            })
            db_session.commit()
            order_id = db_session.execute(text("SELECT @order_id")).scalar()
            print(f"Order ID: {order_id}")
            return f"Order processed successfully. Order ID: {order_id}"

        except exc.SQLAlchemyError as e:
            db_session.rollback()
            return f"Error processing order: {str(e)}", 500
        finally:
            db_session.close()
    return render_template("process_order.html")



@app.route("/register", methods=["POST", "GET"])
def register_customer():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        phone_number = request.form.get("phone_number")
        email = request.form.get("email")
        password = request.form.get("password")

        # Validate password strength
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("register.html")

        password_hash = hash_password(password)

        # Check if email already exists
        db_session = Session()
        existing_customer = db_session.query(Customer).filter_by(email=email).first()
        if existing_customer:
            flash("Email already in use. Please choose a different one.", "error")
            db_session.close()
            return render_template("register.html")

        try:
            # Execute the stored procedure
            result = db_session.execute(
                text("""
                    DECLARE @new_customer_id INT;
                    DECLARE @new_cart_id INT;
                    EXEC usp_register_customer 
                        :first_name, 
                        :last_name, 
                        :phone_number, 
                        :email, 
                        :password_hash, 
                        @new_customer_id OUTPUT, 
                        @new_cart_id OUTPUT;
                    SELECT @new_customer_id AS new_customer_id, @new_cart_id AS new_cart_id;
                """),
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone_number": phone_number,
                    "email": email,
                    "password_hash": password_hash
                }
            )

            # Commit the transaction
            db_session.commit()

            # Fetch the output parameters
            customer_id = result.scalar()  # Get the first value from SELECT (customer_id)
            cart_id = result.scalar()  # Get the second value from SELECT (cart_id)

            print(f"Customer ID: {customer_id}")
            print(f"Cart ID: {cart_id}")

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))

        except SQLAlchemyError as e:
            db_session.rollback()
            flash(f"Error registering customer: {str(e)}", "error")
            return render_template("register.html")
        finally:
            db_session.close()

    return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Your login logic here (e.g., authenticate user, set session, etc.)
        email = request.form.get("email")
        password = request.form.get("password")

        # Perform authentication logic, e.g., compare with stored hashed password

        return redirect(url_for("index"))  # Redirect to home page after successful login

    return render_template("login.html")  # Render login page for GET request

@app.route('/add_to_cart/<int:book_id>', methods=['POST'])
def add_to_cart(book_id):
    # Ensure the user is logged in
    if 'customer_id' not in flask_session or 'cart_id' not in flask_session:
        flash("You need to be logged in to add books to the cart.", "danger")
        return redirect(url_for('login'))

    cart_id = flask_session['cart_id']

    db_session = Session()  # Initialize the SQLAlchemy session
    try:
        # Execute stored procedure to add book to cart
        db_session.execute(
            text("EXEC usp_add_book_to_cart :cart_id, :book_id"),
            {"cart_id": cart_id, "book_id": book_id}
        )
        db_session.commit()

        flash("Book added to cart successfully!", "success")
    except SQLAlchemyError as e:
        db_session.rollback()
        flash(f"An error occurred: {str(e)}", "danger")
    finally:
        db_session.close()

    return redirect(url_for('book_detail', book_id=book_id))