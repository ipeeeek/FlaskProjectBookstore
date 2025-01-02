from flask import request, render_template, session as flask_session, redirect, url_for, flash, jsonify
from app import app, Session
from sqlalchemy import or_, text, exc
from sqlalchemy.exc import SQLAlchemyError
from utils import hash_password, check_password
from werkzeug.security import check_password_hash
from models import Book, Customer, Cart
from models import *

from utils import check_password  # Import your custom check_password function

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
        # Get customer information from the form
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        phone_number = request.form.get("phone_number")
        email = request.form.get("email")
        password = request.form.get("password")

        # Get address information from the form
        street_id = request.form.get("street_id")
        neighborhood_id = request.form.get("neighborhood_id")
        district_id = request.form.get("district_id")
        province_id = request.form.get("province_id")
        country_id = request.form.get("country_id")
        postal_code_id = request.form.get("postal_code_id")

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
            db_session.commit()
            result_data = result.fetchone()  # Fetching both customer_id and cart_id at once
            customer_id = result_data['new_customer_id']
            cart_id = result_data['new_cart_id']

            # Add the shipping address for the newly registered customer
            result = db_session.execute(
                text(""" 
                    DECLARE @shipping_address_id INT;
                    EXEC usp_add_shipping_address 
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
                    "street_id": street_id,
                    "neighborhood_id": neighborhood_id,
                    "district_id": district_id,
                    "province_id": province_id,
                    "country_id": country_id,
                    "postal_code_id": postal_code_id
                }
            )

            # Fetch the shipping address id
            db_session.commit()
            shipping_address_id = result.scalar()  # Fetch the shipping address id

            # If we got the address id, proceed
            if shipping_address_id:
                flash(f"Registration successful! Shipping address added. Address ID: {shipping_address_id}", "success")
                return redirect(url_for("login"))
            else:
                flash("Error: Shipping address not added.", "error")
                return render_template("register.html")

        except SQLAlchemyError as e:
            db_session.rollback()
            flash(f"Error registering customer: {str(e)}", "error")
            return render_template("register.html")
        finally:
            db_session.close()

    # Fetch address-related data for the form
    db_session = Session()
    streets = db_session.query(Street).all()  # Assuming Street model exists
    neighborhoods = db_session.query(Neighborhood).all()  # Assuming Neighborhood model exists
    districts = db_session.query(District).all()  # Assuming District model exists
    provinces = db_session.query(Province).all()  # Assuming Province model exists
    countries = db_session.query(Country).all()  # Assuming Country model exists
    postal_codes = db_session.query(PostalCode).all()  # Assuming PostalCode model exists
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

    # Assuming customer information is stored in the session
    customer_name = flask_session.get('customer_name')
    customer_surname = flask_session.get('customer_surname')
    customer_email = flask_session.get('customer_email')

    # Render the profile page and pass customer data
    return render_template('profile.html',
                           customer_name=customer_name,
                           customer_surname=customer_surname,
                           customer_email=customer_email)

@app.route('/settings')
def settings():  # Changed function name from 'profile' to 'settings'
    return "Settings page is under construction", 200

@app.route('/orders')
def orders():  # Changed function name from 'profile' to 'settings'
    return "Orders page is under construction", 200

@app.route("/add_shipping_address", methods=["POST"])
def add_shipping_address():
    if request.method == "POST":
        street_id = request.form.get("street_id")
        neighborhood_id = request.form.get("neighborhood_id")
        district_id = request.form.get("district_id")
        province_id = request.form.get("province_id")
        country_id = request.form.get("country_id")
        postal_code_id = request.form.get("postal_code_id")

        db_session = Session()
        try:
            # Execute stored procedure to add shipping address
            result = db_session.execute(
                text("""
                    DECLARE @shipping_address_id INT;
                    EXEC usp_add_shipping_address 
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
                    "street_id": street_id,
                    "neighborhood_id": neighborhood_id,
                    "district_id": district_id,
                    "province_id": province_id,
                    "country_id": country_id,
                    "postal_code_id": postal_code_id
                }
            )
            db_session.commit()
            shipping_address_id = result.scalar()  # Get the shipping address ID from the result
            flash(f"Shipping address added successfully. Address ID: {shipping_address_id}", "success")
            return redirect(url_for("profile"))  # Redirect to profile or another page
        except SQLAlchemyError as e:
            db_session.rollback()
            flash(f"An error occurred: {str(e)}", "danger")
            return render_template("add_shipping_address.html")
        finally:
            db_session.close()

    return render_template("add_shipping_address.html")
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
