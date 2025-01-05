from flask import request, render_template, session as flask_session, redirect, url_for, flash, jsonify
from sqlalchemy.orm import joinedload
from datetime import datetime
from app import app, Session
from sqlalchemy import or_, text, exc
from sqlalchemy.exc import SQLAlchemyError
from utils import hash_password, check_password
from models import *
import pyodbc


def get_revenue(start_date=None, end_date=None):
    db_session = Session()
    query = text("""
        SELECT dbo.fn_calculate_revenue(:start_date, :end_date) AS revenue
    """)
    result = db_session.execute(query, {"start_date": start_date, "end_date": end_date}).fetchone()
    db_session.close()

    # Access the result using index, not dictionary key
    return result[0] if result else 0.0
@app.route('/get_provinces', methods=['GET'])
def get_provinces():
    db_session = Session()
    country_id = request.args.get('country_id')
    provinces = db_session.query(Province).filter_by(country_id=country_id).all()
    return jsonify({'provinces': [{'province_id': province.province_id, 'province_name': province.province_name} for province in provinces]})

@app.route('/get_districts', methods=['GET'])
def get_districts():
    db_session = Session()
    province_id = request.args.get('province_id')
    districts = db_session.query(District).filter_by(province_id=province_id).all()
    return jsonify({'districts': [{'district_id': district.district_id, 'district_name': district.district_name} for district in districts]})

@app.route('/get_neighborhoods', methods=['GET'])
def get_neighborhoods():
    db_session = Session()
    district_id = request.args.get('district_id')
    neighborhoods = db_session.query(Neighborhood).filter_by(district_id=district_id).all()
    return jsonify({'neighborhoods': [{'neighborhood_id': neighborhood.neighborhood_id, 'neighborhood_name': neighborhood.neighborhood_name} for neighborhood in neighborhoods]})


@app.route("/get_postal_codes")
def get_postal_codes():
    district_id = request.args.get("district_id")  # Correct: Use district_id

    if not district_id:
        return jsonify({"postal_codes": []})

    db_session = Session()
    postal_codes = db_session.query(PostalCode).filter_by(district_id=district_id).all()
    db_session.close()

    postal_codes_list = [{"postal_code_id": pc.postal_code_id, "postal_code": pc.postal_code} for pc in postal_codes] #Corrected to postal_code_id
    return jsonify({"postal_codes": postal_codes_list})
@app.route('/get_streets', methods=['GET'])
def get_streets():
    db_session = Session()
    neighborhood_id = request.args.get('neighborhood_id')  # Streets are linked to neighborhoods
    streets = db_session.query(Street).filter_by(neighborhood_id=neighborhood_id).all()
    return jsonify({'streets': [{'street_id': street.street_id, 'street_name': street.street_name} for street in streets]})

# Utility functions
def get_customer_by_id(customer_id):
    db_session = Session()
    try:
        customer = db_session.query(Customer).get(customer_id)
        return customer
    except Exception as e:
        print(f"Error getting customer: {e}")
        return None
    finally:
        db_session.close()

def is_customer_valid(email, password):
    """Checks if the provided email and password are valid."""
    db_session = Session()
    try:
        customer = db_session.query(Customer).filter_by(email=email).first()
        if customer and check_password(password, customer.password_hash):  # Use check_password here
            return True
        return False
    except Exception as e:
        print(f"Error during customer validation: {e}")
    finally:
        db_session.close()

def is_admin_valid(email, password):
    """Checks if the provided admin email and password are valid."""
    db_session = Session()
    try:
        admin_user = db_session.query(AdminUser).filter_by(email=email).first()
        if admin_user and check_password(password, admin_user.password_hash):  # Use check_password here
            return True
        return False
    except Exception as e:
        print(f"Error during admin validation: {e}")
    finally:
        db_session.close()


def get_customer_id(email):
    """Retrieves the customer ID for a given email."""
    db_session = Session()
    try:
        customer = db_session.query(Customer).filter_by(email=email).first()
        if customer:
            return customer.customer_id
        return None
    except Exception as e:
        print(f"Error getting customer ID: {e}")
    finally:
        db_session.close()

def get_admin_user_id(email):
    """Retrieves the admin user ID for a given email."""
    db_session = Session()
    try:
        # Query the AdminUser table to find the admin by email
        admin_user = db_session.query(AdminUser).filter_by(email=email).first()
        if admin_user:
            return admin_user.admin_user_id  # Return the admin user ID
        return None  # Return None if no admin user is found
    except Exception as e:
        print(f"Error getting admin user ID: {e}")
    finally:
        db_session.close()  # Ensure the session is closed


def get_cart_id(customer_id):
    """Retrieves the cart ID for a given customer ID."""
    db_session = Session()
    try:
        cart = db_session.query(Cart).filter_by(customer_id=customer_id).first()
        if cart:
            return cart.cart_id
        else:
            new_cart = Cart(customer_id=customer_id)
            db_session.add(new_cart)
            db_session.commit()
            return new_cart.cart_id
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


@app.route("/book/<int:book_id>", methods=["GET"])
def book_detail(book_id):
    db_session = Session()  # Initialize the database session

    # Fetch book details with related data using joinedload for eager loading
    book = db_session.query(Book).options(
        joinedload(Book.dimension),
        joinedload(Book.book_format),
        joinedload(Book.book_language),
        joinedload(Book.publisher)
    ).filter_by(book_id=book_id).first()

    # Check if the book exists
    if not book:
        db_session.close()
        flash("Book not found.", "error")
        return redirect(url_for("index"))  # Redirect to the homepage if the book is not found

    # Fetch the average rating using the SQL Server function
    result = db_session.execute(
        text("SELECT dbo.fn_calculate_average_rating(:book_id) AS average_rating"),
        {'book_id': book_id}
    ).fetchone()
    book.average_rating = round(result.average_rating, 1) if result and result.average_rating is not None else None
    # Check if the user has already rated the book
    already_rated = False
    if 'customer_id' in flask_session:
        customer_id = flask_session['customer_id']
        existing_rating = db_session.query(Rating).filter_by(customer_id=customer_id, book_id=book_id).first()
        if existing_rating:
            already_rated = True

    db_session.close()

    # Render the book detail template with all the relevant data
    return render_template(
        "book.html",
        book=book,
        dimension=book.dimension,
        book_format=book.book_format,
        language=book.book_language,
        publisher=book.publisher
    )

@app.route('/rate_book/<int:book_id>', methods=['POST'])
def rate_book(book_id):
    db_session = Session()
    rating_value = request.form.get('rating', type=int)  # Explicitly convert to int

    # Validate rating value
    if rating_value is None or rating_value < 1 or rating_value > 5:
        return "Invalid rating value. Please select a rating between 1 and 5.", 400

    # Check if the customer is logged in via session
    if 'customer_id' not in flask_session:
        flash("You need to be logged in to rate a book.", "error")
        return redirect(url_for("login"))  # Redirect to login if not logged in

    # Fetch customer data from the session
    customer_id = flask_session['customer_id']

    # Check if the user has already rated this book
    existing_rating = db_session.query(Rating).filter_by(customer_id=customer_id, book_id=book_id).first()
    if existing_rating:
        db_session.close()
        flash("You have already rated this book.", "error")
        return redirect(url_for('book_detail', book_id=book_id))  # Redirect to book detail page if already rated

    # Fetch the book to be rated
    book = db_session.query(Book).filter_by(book_id=book_id).first()
    if not book:
        db_session.close()
        flash("Book not found.", "error")
        return redirect(url_for("index"))  # Redirect to the homepage if book is not found

    # Insert the rating without using OUTPUT clause
    try:
        # Manually perform the insert without using OUTPUT clause
        sql = text("""
            INSERT INTO rating (customer_id, book_id, rating_value, created_at, updated_at)
            VALUES (:customer_id, :book_id, :rating_value, :created_at, :updated_at)
        """)

        db_session.execute(sql, {
            'customer_id': customer_id,
            'book_id': book_id,
            'rating_value': rating_value,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })

        # Commit the transaction
        db_session.commit()

    except Exception as e:
        db_session.rollback()
        print(f"Error while submitting rating: {e}")
        return "An error occurred while submitting your rating.", 500

    db_session.close()
    flash("Your rating has been submitted successfully!", "success")
    return redirect(url_for('book_detail', book_id=book_id))
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


@app.route('/admin/orders')
def view_orders():
    db_session = Session()
    # Check if the admin is logged in by checking the session
    if 'admin_user_id' not in flask_session:
        flash("You must be logged in to access this page.", "error")
        return redirect(url_for('admin_login'))  # Redirect to the login page

    # Fetch all orders from the customer_order table
    orders = db_session.query(CustomerOrder).all()

    return render_template('admin/view_orders.html', orders=orders)

@app.route('/admin/view_order_details/<int:order_id>')
def view_order_details(order_id):
    db_session = Session()

    # Query for the order using the order_id
    order = db_session.query(CustomerOrder).filter(CustomerOrder.customer_order_id == order_id).first()

    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('admin.view_orders'))  # Redirect to orders list if order is not found

    # Retrieve the customer related to the order
    customer = db_session.query(Customer).filter(Customer.customer_id == order.customer_id).first()

    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for('admin.view_orders'))  # Redirect to orders list if customer is not found

    # Retrieve the full address using the fn_format_full_address function
    address_query = text("""
        SELECT dbo.fn_format_full_address(:shipping_address_id) AS full_address
    """)
    result = db_session.execute(address_query, {'shipping_address_id': order.shipping_address_id}).fetchone()

    if result:
        full_address = result[0]  # This will be the first column (full_address)
    else:
        full_address = None

    # Retrieve books associated with the order
    books_query = db_session.query(Book, CustomerOrderBook.quantity).join(CustomerOrderBook).filter(
        CustomerOrderBook.customer_order_id == order.customer_order_id).all()

    books = [{"title": book.title, "quantity": quantity} for book, quantity in books_query]

    # Pass the order, customer, books, and full address to the template
    return render_template('admin/view_order_details.html', order=order, customer=customer, full_address=full_address, books=books)
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

                # Use the function to calculate the total price of the cart
                cart_total_result = db_session.execute(text("""
                    SELECT dbo.fn_calculate_cart_total(:cart_id) AS total_price
                """), {"cart_id": cart.cart_id})

                total_price = cart_total_result.scalar()  # Get the calculated total price

        except SQLAlchemyError as e:
            flash(f"An error occurred: {str(e)}", "danger")
        finally:
            db_session.close()

    return render_template("cart.html", cart_items=cart_items, total_price=total_price)

@app.route("/process_order", methods=["GET", "POST"])
def process_order():
    if request.method == "GET":
        customer_id = flask_session.get('customer_id')
        db_session = Session()

        try:
            # Get cart ID from session and calculate total amount
            cart_id = flask_session.get('cart_id')
            result = db_session.execute(
                text("SELECT dbo.fn_calculate_cart_total(:cart_id) AS cart_total"),
                {"cart_id": cart_id}
            )
            total_amount = result.fetchone()[0]  # Fetch the result and extract total_amount

            # Store total_amount in session
            flask_session['total_amount'] = total_amount

            # Retrieve all shipping addresses for the customer
            addresses = db_session.query(ShippingAddress).filter_by(customer_id=customer_id).all()
            formatted_addresses = [
                {
                    'shipping_address_id': address.shipping_address_id,
                    'full_address': db_session.execute(
                        text("SELECT dbo.fn_format_full_address(:shipping_address_id) AS full_address"),
                        {"shipping_address_id": address.shipping_address_id}
                    ).fetchone()[0]  # Ensure proper fetching of results
                }
                for address in addresses
            ]

            payment_methods = db_session.query(PaymentMethod).all()

            return render_template("process_order.html",
                                   formatted_addresses=formatted_addresses,
                                   payment_methods=payment_methods,
                                   total_amount=total_amount)

        except SQLAlchemyError as e:
            flash(f"Error retrieving data: {str(e)}", "danger")
        finally:
            db_session.close()

    elif request.method == "POST":
        customer_id = flask_session.get('customer_id')
        shipping_address_id = request.form.get('shipping_address_id')
        payment_method_id = request.form.get('payment_method_id')
        total_amount = flask_session.get('total_amount')  # Get total_amount from session

        db_session = Session()
        try:
            # Insert payment record first
            payment = Payment(
                customer_id=customer_id,
                payment_method_id=payment_method_id,
                total_amount=total_amount,
                payment_status_id=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db_session.add(payment)
            db_session.commit()

            # Get the generated payment_id
            payment_id = payment.payment_id

            # Call stored procedure to process the order
            order_id_result = db_session.execute(text(""" 
                DECLARE @order_id INT;
                EXEC usp_process_order 
                    :customer_id, 
                    :shipping_address_id, 
                    :payment_id, 
                    :total_amount, 
                    @order_id OUTPUT;
                SELECT @order_id AS order_id;
            """), {
                "customer_id": customer_id,
                "shipping_address_id": shipping_address_id,
                "payment_id": payment_id,
                "total_amount": total_amount
            })

            # Ensure to fetch the order_id after the procedure executes
            order_id = order_id_result.fetchone()[0]  # Fetch the result properly
            flask_session['order_id'] = order_id

            # Fetch shipping address using the custom function
            shipping_address = db_session.execute(
                text("SELECT dbo.fn_format_full_address(:shipping_address_id) AS full_address"),
                {"shipping_address_id": shipping_address_id}
            ).fetchone()[0]

            payment_method = db_session.query(PaymentMethod).filter_by(payment_method_id=payment_method_id).first()
            order_status = db_session.query(OrderStatus).filter_by(order_status_id=1).first()
            customer_books = db_session.query(CustomerOrderBook).filter_by(customer_order_id=order_id).all()

            # Clear the books from the cart after order is placed (removing items from CustomerOrderBook)
            db_session.query(CustomerOrderBook).filter(CustomerOrderBook.customer_id == customer_id).delete()
            db_session.commit()

            # Clear cart-related session variables
            flask_session.pop('cart_id', None)
            flask_session.pop('total_amount', None)

            flash(f"Your order #{order_id} has been successfully placed!", "success")

            return render_template('order_summary.html',
                                   order_id=order_id,
                                   shipping_address=shipping_address,
                                   payment_method=payment_method,
                                   order_status=order_status,
                                   customer_books=customer_books)

        except pyodbc.Error as e:
            flash(f"Error processing payment: {str(e)}", "danger")
            return render_template('order_summary.html', error="There was an error processing your payment.")

        except SQLAlchemyError as e:
            db_session.rollback()
            flash(f"Error processing order: {str(e)}", "danger")
            return render_template('order_summary.html', error="There was an error processing your order.")

        finally:
            db_session.close()

@app.route("/register", methods=["POST", "GET"])
def register_customer():
    if request.method == "POST":
        # Get customer information from the form
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        phone_number = request.form.get("phone_number")
        email = request.form.get("email")
        password = request.form.get("password")

        # Get address information from the form
        street_id = int(request.form.get("street_id"))
        neighborhood_id = int(request.form.get("neighborhood_id"))
        district_id = int(request.form.get("district_id"))
        province_id = int(request.form.get("province_id"))
        country_id = int(request.form.get("country_id"))
        postal_code_id = int(request.form.get("postal_code_id"))

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
            # Execute the customer registration stored procedure
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

            # Fetch the customer_id and cart_id from the result
            result_data = result.fetchone()

            # Access the values by index (0 for new_customer_id, 1 for new_cart_id)
            customer_id = result_data[0]  # First column is new_customer_id
            cart_id = result_data[1]  # Second column is new_cart_id

            if not customer_id:
                flash("Customer registration failed, invalid customer ID.", "error")
                return render_template("register.html")

            # Add the shipping address for the newly registered customer
            result = db_session.execute(
                text("""
                    DECLARE @shipping_address_id INT;
                    EXEC usp_add_shipping_address
                        :customer_id,
                        :street_id,
                        :neighborhood_id,
                        :district_id,
                        :province_id,
                        :country_id,
                        :postal_code_id,
                        @shipping_address_id OUTPUT;
                    SELECT @shipping_address_id AS shipping_address_id;
                """),
                {
                    "customer_id": customer_id,
                    "street_id": street_id,
                    "neighborhood_id": neighborhood_id,
                    "district_id": district_id,
                    "province_id": province_id,
                    "country_id": country_id,
                    "postal_code_id": postal_code_id
                }
            )

            # Commit the shipping address insertion
            db_session.commit()

            # Fetch the shipping address ID
            shipping_address_id = result.scalar()  # Get the shipping address id (scalar will return the first value)

            # If we got the address id, proceed
            if shipping_address_id:
                flash(f"Registration successful! Shipping address added. Address ID: {shipping_address_id}", "success")
                return redirect(url_for("login"))
            else:
                flash("Error: Shipping address not added.", "error")
                return render_template("register.html")

        except SQLAlchemyError as e:
            db_session.rollback()
            error_message = str(e.__dict__['orig'])

            # Check if the error is the specific one (HY010) and mute it
            if "HY010" in error_message:
                flash("Registration successful! You can now log in.", "success")
            else:
                flash(f"Error registering customer: {error_message}", "error")
            return render_template("login.html")

        finally:
            db_session.close()

    # Fetch address-related data for the form
    db_session = Session()
    streets = db_session.query(Street).all()
    neighborhoods = db_session.query(Neighborhood).all()
    districts = db_session.query(District).all()
    provinces = db_session.query(Province).all()
    countries = db_session.query(Country).all()
    postal_codes = db_session.query(PostalCode).all()
    db_session.close()

    return render_template("register.html", streets=streets, neighborhoods=neighborhoods, districts=districts, provinces=provinces, countries=countries, postal_codes=postal_codes)


@app.route('/add_to_cart/<int:book_id>', methods=['POST'])
def add_to_cart(book_id):
    if 'customer_id' not in flask_session or 'cart_id' not in flask_session:
        flash("You need to be logged in to add books to the cart.", "danger")
        return redirect(url_for('login'))

    cart_id = flask_session['cart_id']

    db_session = Session()  # Initialize the SQLAlchemy session
    try:
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

    return redirect(url_for('view_cart'))  # Redirect to the cart page


@app.route("/remove_from_cart/<int:book_id>", methods=["GET"])
def remove_from_cart(book_id):
    if 'customer_id' not in flask_session or 'cart_id' not in flask_session:
        flash("You need to be logged in to remove books from the cart.", "danger")
        return redirect(url_for('login'))

    cart_id = flask_session['cart_id']

    db_session = Session()  # Initialize the SQLAlchemy session
    try:
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
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        # Retrieve email and password from the login form
        email = request.form.get("email")
        password = request.form.get("password")

        # Validate the customer's credentials
        if is_customer_valid(email, password):
            # Get the customer ID from the database or other source
            customer_id = get_customer_id(email)

            # Query the database for the customer object
            db_session = Session()
            customer = db_session.query(Customer).filter_by(customer_id=customer_id).first()
            db_session.close()

            # If customer exists, store the necessary data in the session
            if customer:
                flask_session['customer_id'] = customer_id
                flask_session['customer_name'] = customer.first_name
                flask_session['customer_surname'] = customer.last_name
                flask_session['customer_email'] = customer.email  # Optionally store the email in the session

                # Get the cart ID for the logged-in customer
                cart_id = get_cart_id(customer_id)
                flask_session['cart_id'] = cart_id

                # Flash success message
                flash("Login successful!", "success")
                return redirect(url_for("index"))  # Redirect to the index page

            else:
                flash("Customer not found.", "error")
                return render_template("login.html")  # Return to login if customer not found

        else:
            # If credentials are invalid, show error message
            flash("Invalid email or password", "error")
            return render_template("login.html")  # Return to login page with error message

    # Handle GET request by rendering the login page
    return render_template("login.html")
@app.route("/logout")
def logout():
    flask_session.clear()  # Clear all session data
    flash("You have logged out.", "success")
    return redirect(url_for("index"))
@app.route('/profile')
def profile():
    # Check if the user is logged in (assuming customer session is used)
    if 'customer_id' not in flask_session:
        flash('You need to log in first!', 'warning')
        return redirect(url_for('login'))  # Redirect to login page if not logged in

    customer_id = flask_session.get('customer_id')
    customer_name = flask_session.get('customer_name')
    customer_surname = flask_session.get('customer_surname')
    customer_email = flask_session.get('customer_email')

    db_session = Session()
    try:
        # Get all shipping addresses for the customer
        addresses = db_session.query(ShippingAddress).filter_by(customer_id=customer_id).all()

        # Use the database function to format addresses
        formatted_addresses = []
        for address in addresses:
            result = db_session.execute(
                text("SELECT dbo.fn_format_full_address(:shipping_address_id) AS full_address"),
                {"shipping_address_id": address.shipping_address_id}
            ).fetchone()

            if result:
                # Access the tuple's first element (formatted address)
                formatted_addresses.append(result[0])

    except Exception as e:
        flash(f"Error retrieving addresses: {str(e)}", "error")
        formatted_addresses = []
    finally:
        db_session.close()

    # Render the profile page and pass customer data
    return render_template(
        'profile.html',
        customer_name=customer_name,
        customer_surname=customer_surname,
        customer_email=customer_email,
        addresses=formatted_addresses
    )

@app.route('/add_address', methods=['GET', 'POST'])
def add_address():
    # Ensure the user is logged in
    if 'customer_id' not in flask_session:
        flash('You need to log in first!', 'warning')
        return redirect(url_for('login'))  # Redirect to login if not logged in

    if request.method == 'POST':
        # Get form data
        street_id = request.form.get('street_id')
        neighborhood_id = request.form.get('neighborhood_id')
        district_id = request.form.get('district_id')
        province_id = request.form.get('province_id')
        country_id = request.form.get('country_id')
        postal_code_id = request.form.get('postal_code_id')
        customer_id = flask_session.get('customer_id')

        db_session = Session()
        try:
            # Call the stored procedure to add a new address
            result = db_session.execute(
                text("""
                    DECLARE @shipping_address_id INT;
                    EXEC usp_add_shipping_address
                        :customer_id,
                        :street_id,
                        :neighborhood_id,
                        :district_id,
                        :province_id,
                        :country_id,
                        :postal_code_id,
                        @shipping_address_id OUTPUT;
                    SELECT @shipping_address_id AS shipping_address_id;
                """),
                {
                    "customer_id": customer_id,
                    "street_id": street_id,
                    "neighborhood_id": neighborhood_id,
                    "district_id": district_id,
                    "province_id": province_id,
                    "country_id": country_id,
                    "postal_code_id": postal_code_id
                }
            )

            # Commit the transaction
            db_session.commit()

            # Get the new address ID
            shipping_address_id = result.scalar()

            if shipping_address_id:
                flash("New address added successfully!", "success")
                return redirect(url_for('profile'))
            else:
                flash("Failed to add new address.", "error")
        except Exception as e:
            db_session.rollback()
            flash(f"Error adding new address: {e}", "error")
        finally:
            db_session.close()

    # Fetch address-related data for the dropdowns
    db_session = Session()
    streets = db_session.query(Street).all()
    neighborhoods = db_session.query(Neighborhood).all()
    districts = db_session.query(District).all()
    provinces = db_session.query(Province).all()
    countries = db_session.query(Country).all()
    postal_codes = db_session.query(PostalCode).all()
    db_session.close()

    return render_template('add_address.html', streets=streets, neighborhoods=neighborhoods, districts=districts, provinces=provinces, countries=countries, postal_codes=postal_codes)

@app.route('/settings')
def settings():  # Changed function name from 'profile' to 'settings'
    return "Settings page is under construction", 200

@app.route('/orders', methods=['GET'])
def orders():
    db_session = Session()  # Assuming this is a SQLAlchemy session instance
    # Ensure the user is logged in
    if 'customer_id' not in flask_session:
        flash('You need to log in to view your orders.')
        return redirect(url_for('login'))

    customer_id = flask_session.get('customer_id')  # Access session data correctly
    try:
        # Query the orders for the current customer
        orders_query = db_session.execute(text(""" 
            SELECT 
                co.customer_order_id,
                co.shipping_address_id,
                co.total_amount,
                co.created_at,
                os.order_status_name AS order_status_name
            FROM customer_order co
            JOIN order_status os ON co.order_status_id = os.order_status_id
            WHERE co.customer_id = :customer_id
        """), {"customer_id": customer_id}).fetchall()

        orders = []
        for order in orders_query:
            # Fetch the full formatted address
            full_address_result = db_session.execute(text(""" 
                SELECT dbo.fn_format_full_address(:shipping_address_id) AS full_address
            """), {"shipping_address_id": order.shipping_address_id}).fetchone()
            full_address = full_address_result.full_address if full_address_result else "Address Not Available"

            # Query the books associated with the order
            books_query = db_session.execute(text(""" 
                SELECT 
                    b.title,
                    cob.quantity
                FROM customer_order_book cob
                JOIN book b ON cob.book_id = b.book_id
                WHERE cob.customer_order_id = :customer_order_id
            """), {"customer_order_id": order.customer_order_id}).fetchall()

            books = [{"title": book.title, "quantity": book.quantity} for book in books_query]

            # Add the order details to the list
            orders.append({
                "order_id": order.customer_order_id,
                "created_at": order.created_at,
                "total_amount": order.total_amount,
                "order_status_name": order.order_status_name,
                "shipping_address": full_address,
                "books": books
            })

        return render_template('orders.html', orders=orders)
    except Exception as e:
        # Log and show error if something goes wrong
        print(f"Error retrieving orders: {e}")
        flash('Error retrieving orders.')
        return render_template('orders.html', orders=[])

@app.route('/update_customer', methods=['POST'])
def update_customer():
    # Retrieve the updated phone number and email from the form
    new_phone_number = request.form['new_phone_number']
    new_email = request.form['new_email']
    customer_id = flask_session['customer_id']  # Assuming the customer is logged in

    # Check if the email already exists in the database
    db_session = Session()  # Initialize the session here
    existing_customer = db_session.query(Customer).filter_by(email=new_email).first()

    if existing_customer:
        flash("This email is already in use. Please choose a different one.", 'error')
        db_session.close()
        return redirect(url_for('profile'))

    # Now proceed to update the customer's information in the database
    try:
        # Call the stored procedure for updating customer info
        db_session.execute(
            text("EXEC usp_update_customer :customer_id, :new_phone_number, :new_email"),
            {"customer_id": customer_id, "new_phone_number": new_phone_number, "new_email": new_email}
        )
        db_session.commit()

        flash("Your information has been updated successfully.", 'success')
        return redirect(url_for('profile'))

    except Exception as e:
        db_session.rollback()
        flash("An error occurred while updating your information.", 'error')
        return redirect(url_for('profile'))
    finally:
        db_session.close()

@app.route("/update_customer_password", methods=["POST"])
def update_customer_password():
    if 'customer_id' not in flask_session:
        flash("You need to be logged in to update your password.", "danger")
        return redirect(url_for('login'))

    customer_id = flask_session['customer_id']
    new_password = request.form.get("new_password")
    hashed_password = hash_password(new_password)  # Hash the new password before storing it

    db_session = Session()
    try:
        # Execute stored procedure to update customer password
        db_session.execute(
            text("""
                EXEC usp_update_customer_password 
                    :customer_id, 
                    :new_password;
            """),
            {
                "customer_id": customer_id,
                "new_password": hashed_password
            }
        )
        db_session.commit()
        flash("Password updated successfully!", "success")
        return redirect(url_for("profile"))  # Redirect to the profile page
    except SQLAlchemyError as e:
        db_session.rollback()
        flash(f"An error occurred: {str(e)}", "danger")
        return render_template("update_password.html")
    finally:
        db_session.close()

@app.route("/update_admin_password", methods=["POST"])
def update_admin_password():
    if 'admin_user_id' not in flask_session:
        flash("You need to be logged in as an admin to update the password.", "danger")
        return redirect(url_for('admin_login'))

    admin_user_id = flask_session['admin_user_id']
    new_password = request.form.get("new_password")
    hashed_password = hash_password(new_password)  # Hash the new password before storing it

    db_session = Session()
    try:
        # Execute stored procedure to update admin password
        db_session.execute(
            text("""
                EXEC usp_update_admin_password 
                    :admin_user_id, 
                    :new_password;
            """),
            {
                "admin_user_id": admin_user_id,
                "new_password": hashed_password
            }
        )
        db_session.commit()
        flash("Admin password updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))  # Redirect to the admin dashboard
    except SQLAlchemyError as e:
        db_session.rollback()
        flash(f"An error occurred: {str(e)}", "danger")
        return render_template("update_admin_password.html")
    finally:
        db_session.close()

from flask import render_template

@app.route('/order_summary')
def order_summary():
    # Retrieve the customer_id from session
    customer_id = flask_session.get('customer_id')

    if not customer_id:
        return "Customer not found", 404  # Handle case when customer_id is not available in session

    db_session = Session()
    try:
        # Fetch the latest order for the customer
        order = db_session.query(CustomerOrder, ShippingAddress, PaymentMethod, OrderStatus). \
            join(ShippingAddress, ShippingAddress.shipping_address_id == CustomerOrder.shipping_address_id). \
            join(PaymentMethod, PaymentMethod.payment_method_id == CustomerOrder.payment_id). \
            join(OrderStatus, OrderStatus.order_status_id == CustomerOrder.order_status_id). \
            filter(CustomerOrder.customer_id == customer_id). \
            order_by(CustomerOrder.created_at.desc()). \
            first()  # Get the most recent order for the customer

        if not order:
            return "Order not found", 404  # Handle case where no order is found for this customer

        # Call the custom SQL function to get the formatted full address
        full_address = db_session.execute(
            text("SELECT dbo.fn_format_full_address(:shipping_address_id) AS full_address"),
            {"shipping_address_id": order.CustomerOrder.shipping_address_id}
        ).fetchone()[0]  # Fetch the formatted address from the result

        # Get the books associated with this order by joining customer_order_book and book
        order_books = db_session.query(Book, CustomerOrderBook.quantity). \
            join(CustomerOrderBook, CustomerOrderBook.book_id == Book.book_id). \
            filter(CustomerOrderBook.customer_order_id == order.CustomerOrder.customer_order_id). \
            all()  # Get all books in the order

        # Extract order details
        total_amount = order.CustomerOrder.total_amount
        payment_method = order.PaymentMethod.payment_method_name  # Example, adjust to your schema
        order_status = order.OrderStatus.order_status_name  # Corrected to 'order_status_name'

        # Pass the data to the template
        return render_template('order_summary.html',
                               order_books=order_books,
                               total_amount=total_amount,
                               shipping_address=full_address,  # Use the full address from the function
                               payment_method=payment_method,
                               order_status=order_status)

    except SQLAlchemyError as e:
        return f"Error retrieving order details: {str(e)}", 500  # Error handling for DB query
    finally:
        db_session.close()


from flask import redirect, url_for


@app.route("/admin/login", methods=["POST", "GET"])
def admin_login():
    if request.method == "POST":
        # Retrieve email and password from the login form
        email = request.form.get("email")
        password = request.form.get("password")

        # Validate the admin's credentials
        if is_admin_valid(email, password):
            # Get the admin user ID from the database
            admin_user_id = get_admin_user_id(email)

            # Query the database for the admin object
            db_session = Session()
            admin_user = db_session.query(AdminUser).filter_by(admin_user_id=admin_user_id).first()
            db_session.close()

            # If admin exists, store the necessary data in the session
            if admin_user:
                flask_session['admin_user_id'] = admin_user_id
                flask_session['admin_user_name'] = admin_user.first_name
                flask_session['admin_user_surname'] = admin_user.last_name
                flask_session['admin_user_email'] = admin_user.email  # Optionally store the email in the session

                # Flash success message
                flash("Login successful!", "success")

                # Redirect to the admin dashboard page
                return redirect(url_for('admin_dashboard'))  # Correct redirect to dashboard

            else:
                flash("Admin user not found.", "error")
                return render_template("admin/login.html")  # Return to login if admin user not found

        else:
            # If credentials are invalid, show error message
            flash("Invalid email or password", "error")
            return render_template("admin/login.html")  # Return to login page with error message

    # Handle GET request by rendering the login page
    return render_template("admin/login.html")


@app.route("/admin/register", methods=["POST", "GET"])
def register_admin():
    if request.method == "POST":
        # Get admin user information from the form
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")

        # Validate password strength
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("admin/register.html")

        password_hash = hash_password(password)

        # Check if email already exists
        db_session = Session()
        existing_admin = db_session.query(AdminUser).filter_by(email=email).first()

        if existing_admin:
            flash("Email already in use. Please choose a different one.", "error")
            db_session.close()
            return render_template("admin/register.html")

        try:
            # Create a new AdminUser instance
            new_admin_user = AdminUser(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password_hash=password_hash,
                last_login=None,  # Optional: Set to None initially
                created_at=datetime.now(),  # Current timestamp
                updated_at=datetime.now()   # Current timestamp
            )

            # Add the new admin user to the session
            db_session.add(new_admin_user)
            db_session.commit()

            flash(f"Admin registration successful! Admin User ID: {new_admin_user.admin_user_id}", "success")
            return redirect(url_for("admin_login"))

        except SQLAlchemyError as e:
            db_session.rollback()
            error_message = str(e.__dict__['orig'])
            flash(f"Error registering admin: {error_message}", "error")
            return render_template("admin/register.html")

        finally:
            db_session.close()

    return render_template("admin/register.html")

@app.route('/admin/dashboard')
def admin_dashboard():
    db_session = Session()
    if 'admin_user_id' not in flask_session:
        flash("You must be logged in to access this page.", "error")
        return redirect(url_for('admin_login'))

    # Fetch admin details from session
    admin_name = flask_session.get('admin_user_name')
    admin_surname = flask_session.get('admin_user_surname')
    admin_email = flask_session.get('admin_user_email')

    # Get total revenue (you can specify start_date and end_date if needed)
    revenue = get_revenue()

    return render_template('admin/dashboard.html', admin_name=admin_name, admin_surname=admin_surname, admin_email=admin_email, revenue=revenue)
@app.route('/admin/add_book', methods=['GET', 'POST'])
def add_book():
    db_session = Session()

    if request.method == 'POST':
        try:
            # Retrieve form data
            title = request.form['title']
            isbn = request.form['isbn']
            publication_date = request.form['publication_date']
            cover_image_path = request.form['cover_image_path']
            synopsis = request.form['synopsis']
            price = request.form['price']
            stock_quantity = request.form['stock_quantity']
            page_count = request.form['page_count']
            author_id = request.form['author_id']  # Get author_id from the form

            # Retrieve the selected values for dropdown options
            dimension_id = request.form['dimension_id']
            book_format_id = request.form['book_format_id']
            book_language_id = request.form['book_language_id']
            publisher_id = request.form['publisher_id']

            # Execute the stored procedure to insert the new book
            conn = db_session.connection()
            result = conn.execute(
                text("""
                    DECLARE @new_book_id INT;
                    EXEC usp_add_book :title, :isbn, :publication_date, :cover_image_path, 
                                       :synopsis, :price, :stock_quantity, :page_count, NULL, 
                                       :dimension_id, :book_format_id, :book_language_id, :publisher_id, 
                                       @new_book_id OUTPUT;
                    SELECT @new_book_id AS new_book_id;
                """),
                {
                    'title': title,
                    'isbn': isbn,
                    'publication_date': publication_date,
                    'cover_image_path': cover_image_path,
                    'synopsis': synopsis,
                    'price': price,
                    'stock_quantity': stock_quantity,
                    'page_count': page_count,
                    'dimension_id': dimension_id,
                    'book_format_id': book_format_id,
                    'book_language_id': book_language_id,
                    'publisher_id': publisher_id
                }
            )

            # Retrieve the newly inserted book's ID
            new_book_id = result.scalar()

            if not new_book_id:
                raise ValueError("Failed to retrieve new book ID. The book was not inserted correctly.")

            # Link the book to the author AFTER the book is created
            conn.execute(
                text("""
                    INSERT INTO book_author (book_id, author_id, created_at, updated_at)
                    VALUES (:book_id, :author_id, GETDATE(), GETDATE())
                """),
                {'book_id': new_book_id, 'author_id': author_id}
            )

            conn.commit()  # Commit the transaction
            flash('Book added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            db_session.rollback()  # Rollback on error
            flash(f'Error adding book: {str(e)}', 'danger')
            return redirect(url_for('add_book'))  # Redirect to the form again

        finally:
            db_session.close()

    # GET request: Render the form
    dimensions = db_session.query(Dimension).all()
    book_formats = db_session.query(BookFormat).all()
    book_languages = db_session.query(BookLanguage).all()
    publishers = db_session.query(Publisher).all()
    authors = db_session.query(Author).all()
    db_session.close()

    return render_template(
        'admin/add_book.html',
        dimensions=dimensions,
        book_formats=book_formats,
        book_languages=book_languages,
        publishers=publishers,
        authors=authors
    )

@app.route('/admin/add_author', methods=['GET', 'POST'])
def add_author():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        bio = request.form.get('bio')  # Optional field
        path_to_image = request.form.get('path_to_image')  # Optional field

        db_session = Session()  # Start a session
        try:
            # Check if the author already exists
            existing_author = db_session.query(Author).filter_by(first_name=first_name, last_name=last_name).first()
            if existing_author:
                flash('Author already exists!', 'warning')
                return redirect(url_for('add_author'))

            # Add the new author with explicit timestamps
            new_author = Author(
                first_name=first_name,
                last_name=last_name,
                bio=bio,
                path_to_image=path_to_image,
                created_at=datetime.utcnow(),  # Explicitly set created_at
                updated_at=datetime.utcnow()   # Explicitly set updated_at
            )
            db_session.add(new_author)
            db_session.commit()
            flash('Author added successfully!', 'success')
        except Exception as e:
            db_session.rollback()
            flash(f'Error adding author: {str(e)}', 'danger')
        finally:
            db_session.close()

        return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_author.html')

@app.route('/admin/update_book/<int:book_id>', methods=['GET', 'POST'])
def update_book(book_id):
    db_session = Session()

    # Fetch the book to edit
    book = db_session.query(Book).filter_by(book_id=book_id).first()

    if not book:
        flash('Book not found!', 'danger')
        return redirect(url_for('view_inventory'))

    # Fetch related data for dropdowns
    dimensions = db_session.query(Dimension).all()
    book_formats = db_session.query(BookFormat).all()
    book_languages = db_session.query(BookLanguage).all()
    publishers = db_session.query(Publisher).all()
    authors = db_session.query(Author).all()

    if request.method == 'POST':
        try:
            title = request.form['title']
            isbn = request.form['isbn']
            publication_date = request.form['publication_date']
            cover_image_path = request.form['cover_image_path']
            synopsis = request.form['synopsis']
            price = request.form['price']
            stock_quantity = request.form['stock_quantity']
            page_count = request.form['page_count']
            dimension_id = request.form['dimension_id']
            book_format_id = request.form['book_format_id']
            book_language_id = request.form['book_language_id']
            publisher_id = request.form['publisher_id']
            author_id = request.form['author_id']

            # Using the stored procedure for update
            conn = db_session.connection()
            result = conn.execute(
                text("""
                    EXEC usp_update_book :book_id, :title, :isbn, :publication_date, :cover_image_path, 
                                         :synopsis, :price, :stock_quantity, :page_count
                """),
                {
                    'book_id': book_id,
                    'title': title,
                    'isbn': isbn,
                    'publication_date': publication_date,
                    'cover_image_path': cover_image_path,
                    'synopsis': synopsis,
                    'price': price,
                    'stock_quantity': stock_quantity,
                    'page_count': page_count
                }
            )

            db_session.commit()
            flash('Book updated successfully!', 'success')
            return redirect(url_for('view_inventory'))  # Redirect back to the inventory view

        except Exception as e:
            db_session.rollback()
            flash(f'Error updating book: {str(e)}', 'danger')
            return redirect(url_for('update_book', book_id=book_id))  # Redirect back to edit form

        finally:
            db_session.close()

    # GET request: Render the form with current book details
    return render_template('admin/update_book.html', book=book, dimensions=dimensions,
                           book_formats=book_formats, book_languages=book_languages,
                           publishers=publishers, authors=authors)

@app.route('/admin/remove_book/<int:book_id>', methods=['POST'])
def remove_book(book_id):
    db_session = Session()

    try:
        # Execute the stored procedure to remove the book
        conn = db_session.connection()
        conn.execute(
            text("""
                EXEC usp_remove_book :book_id
            """),
            {'book_id': book_id}
        )

        db_session.commit()
        flash('Book removed successfully!', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'Error removing book: {str(e)}', 'danger')
    finally:
        db_session.close()

    return redirect(url_for('view_inventory'))  # Redirect back to the inventory view

from sqlalchemy import text

@app.route('/admin/out_of_stock_books')
def out_of_stock_books():
    db_session = Session()

    try:
        # Execute the SQL query to get out-of-stock books
        query = text("SELECT * FROM dbo.vw_out_of_stock_books")
        out_of_stock_books = db_session.execute(query).fetchall()

        # Log the results for debugging
        if out_of_stock_books:
            print("Out of stock books:", out_of_stock_books)
        else:
            print("No out of stock books found.")

        # Pass the results to the template
        return render_template('admin/out_of_stock_books.html', out_of_stock_books=out_of_stock_books)

    except Exception as e:
        flash(f'Error fetching out-of-stock books: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))  # Redirect back to the admin dashboard in case of an error

    finally:
        db_session.close()

@app.route('/admin/sold_books')
def sold_books():
    db_session = Session()

    try:
        # Execute the SQL query to get sold books
        query = text("SELECT * FROM dbo.vw_sold_books")
        sold_books = db_session.execute(query).fetchall()

        # Log the results for debugging
        if sold_books:
            print("Sold books:", sold_books)
        else:
            print("No sold books found.")

        # Pass the results to the template
        return render_template('admin/sold_books.html', sold_books=sold_books)

    except Exception as e:
        flash(f'Error fetching sold books: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))  # Redirect back to the admin dashboard in case of an error

    finally:
        db_session.close()

@app.route('/admin/inventory', methods=['GET'])
def view_inventory():
    db_session = Session()

    try:
        # Fetch all books from the database
        books = db_session.query(Book).all()

        # Prepare a dictionary to store sales tax for each book
        sales_tax = {}

        for book in books:
            # Call the fn_calculate_sales_tax function for each book using raw SQL
            result = db_session.execute(
                text("SELECT dbo.fn_calculate_sales_tax(:book_id)"),
                {"book_id": book.book_id}
            )
            # Get the sales tax value from the result
            sales_tax_value = result.scalar()  # .scalar() to get the first column of the first row

            # Store the sales tax value in the dictionary
            sales_tax[book.book_id] = sales_tax_value

    finally:
        db_session.close()

    return render_template('admin/inventory.html', books=books, sales_tax=sales_tax)