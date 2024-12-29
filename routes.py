from flask import request, render_template, session as flask_session, redirect, url_for, flash
from app import app, Session
from sqlalchemy import or_, text, exc
from sqlalchemy.exc import SQLAlchemyError
from utils import hash_password
from werkzeug.security import check_password_hash
from models import Book, Customer, Cart
from models import *

from utils import check_password  # Import your custom check_password function

def is_user_valid(email, password):
    """Checks if the provided email and password are valid."""
    db_session = Session()
    try:
        customer = db_session.query(Customer).filter_by(email=email).first()
        if customer and check_password(password, customer.password_hash):  # Use your check_password function here
            return True
        return False
    except Exception as e:
        print(f"Error during user validation: {e}")
    finally:
        db_session.close()


def get_customer_id(email):
    """Retrieves the customer ID for a given email."""
    db_session = Session()
    try:
        customer = db_session.query(Customer).filter_by(email=email).first()
        if customer:
            return customer.customer_id  # Assuming customer_id is the primary key
        return None
    except Exception as e:
        print(f"Error getting customer ID: {e}")
    finally:
        db_session.close()

def get_cart_id(customer_id):
    """Retrieves the cart ID for a given customer ID."""
    db_session = Session()
    try:
        # Assuming you have a Cart model with a foreign key to Customer
        cart = db_session.query(Cart).filter_by(customer_id=customer_id).first()
        if cart:
            return cart.cart_id  # Return cart ID if cart exists
        else:  # If customer doesn't have a cart, create one
            new_cart = Cart(customer_id=customer_id)
            db_session.add(new_cart)
            db_session.commit()
            return new_cart.cart_id  # Return the ID of the newly created cart
    except Exception as e:
        print(f"Error getting cart ID: {e}")
    finally:
        db_session.close()

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
    if 'customer_id' in flask_session:  # Ensure the user is logged in
        customer_id = flask_session['customer_id']

        db_session = Session()  # Initialize the SQLAlchemy session
        try:
            # Query the cart of the customer
            cart = db_session.query(Cart).filter_by(customer_id=customer_id).first()
            if cart:
                # Assuming CartBook is a relationship with the Cart and Book models
                cart_books = db_session.query(CartBook).filter_by(cart_id=cart.cart_id).all()
                if cart_books:
                    for cart_book in cart_books:
                        book = db_session.query(Book).get(cart_book.book_id)  # Get the book details
                        if book:
                            cart_items.append({"book": book, "quantity": cart_book.quantity})
                            total_price += book.price * cart_book.quantity
        except SQLAlchemyError as e:
            flash(f"An error occurred: {str(e)}", "danger")
        finally:
            db_session.close()

    return render_template("cart.html", cart_items=cart_items, total_price=total_price)

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
        email = request.form.get("email")
        password = request.form.get("password")

        # Your authentication logic here (e.g., compare with stored hashed password)

        if is_user_valid(email, password):  # Replace with your authentication logic
            # Login successful, set session variables
            customer_id = get_customer_id(email)  # Replace with function to get customer ID
            cart_id = get_cart_id(customer_id)  # Replace with function to get cart ID
            flask_session['customer_id'] = customer_id
            flask_session['cart_id'] = cart_id

            flash("Login successful!", "success")
            return redirect(url_for("index"))  # Redirect to desired page after login
        else:
            flash("Invalid login credentials.", "error")
            return render_template("login.html")

    return render_template("login.html")  # Render login page for GET request
@app.route('/add_to_cart/<int:book_id>', methods=['POST'])
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

    # Instead of redirecting to the book details page, redirect back to the cart
    return redirect(url_for('view_cart'))  # Redirect to the cart page

@app.route("/remove_from_cart/<int:book_id>", methods=["GET"])
def remove_from_cart(book_id):
    if 'customer_id' not in flask_session or 'cart_id' not in flask_session:
        flash("You need to be logged in to remove books from the cart.", "danger")
        return redirect(url_for('login'))

    cart_id = flask_session['cart_id']

    db_session = Session()  # Initialize the SQLAlchemy session
    try:
        # Execute stored procedure to remove book from cart
        db_session.execute(
            text("EXEC usp_remove_book_from_cart :cart_id, :book_id"),
            {"cart_id": cart_id, "book_id": book_id}
        )
        db_session.commit()

        flash("Book removed from cart successfully!", "success")
    except SQLAlchemyError as e:
        db_session.rollback()
        flash(f"An error occurred: {str(e)}", "danger")
    finally:
        db_session.close()

    # Redirect to the view_cart page
    return redirect(url_for("view_cart"))

@app.route("/remove_all_from_cart/<int:book_id>", methods=["GET"])
def remove_all_from_cart(book_id):
    """Removes all instances of a specific book from the user's cart."""

    if 'customer_id' not in flask_session or 'cart_id' not in flask_session:
        flash("You need to be logged in to remove books from the cart.", "danger")
        return redirect(url_for('login'))

    cart_id = flask_session['cart_id']
    db_session = Session()

    try:
        # Efficiently delete all matching CartBook entries for the specific book in the cart
        deleted_count = db_session.query(CartBook).filter_by(cart_id=cart_id, book_id=book_id).delete()
        db_session.commit()

        if deleted_count > 0:
            flash(f"All instances of '{book_id}' have been removed from your cart.", "success")
        else:
            flash("This book is not in your cart.", "info")

    except SQLAlchemyError as e:
        db_session.rollback()
        flash(f"An error occurred: {str(e)}", "danger")
    finally:
        db_session.close()

    return redirect(url_for("view_cart"))
