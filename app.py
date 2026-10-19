from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
from functools import wraps

app = Flask(__name__)

app.secret_key = "shopkart-secret-key"

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            flash("Please login first.")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if session.get("role") != "admin":
            flash("Admin access required.")
            return redirect(url_for("index"))

        return function(*args, **kwargs)

    return wrapper
@app.route("/")
def index():

    search_query = request.args.get("q", "")
    selected_category = request.args.get("category", "")

    db = get_db()

    cursor = db.cursor(dictionary=True)

    # Get all categories
    cursor.execute(
        """
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL
        AND category != ''
        ORDER BY category
        """
    )

    categories = cursor.fetchall()

    # Search + Category Filter
    query = """
        SELECT * FROM products
        WHERE 1=1
    """

    values = []

    if search_query:

        query += """
            AND (
                name LIKE %s
                OR description LIKE %s
                OR category LIKE %s
            )
        """

        search_value = f"%{search_query}%"

        values.extend([
            search_value,
            search_value,
            search_value
        ])

    if selected_category:

        query += """
            AND category = %s
        """

        values.append(selected_category)

    query += " ORDER BY id DESC"

    cursor.execute(query, values)

    products = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        search_query=search_query,
        selected_category=selected_category
    )

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Check fields

        if not name or not email or not password:

            flash("Please fill all fields.")

            return redirect(
                url_for("register")
            )

        # Check password

        if password != confirm_password:

            flash("Passwords do not match.")

            return redirect(
                url_for("register")
            )

        # Password length

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters."
            )

            return redirect(
                url_for("register")
            )

        db = get_db()

        cursor = db.cursor()

        # Check existing email

        cursor.execute(
            "SELECT id FROM users WHERE email=%s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            db.close()

            flash("Email already registered.")

            return redirect(
                url_for("register")
            )

        # Hash password

        hashed_password = generate_password_hash(
            password
        )

        # Insert user

        cursor.execute(
            """
            INSERT INTO users
            (name, email, password, role)
            VALUES (%s, %s, %s, %s)
            """,
            (
                name,
                email,
                hashed_password,
                "user"
            )
        )

        db.commit()

        cursor.close()
        db.close()

        flash(
            "Registration successful! Please login."
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:

            flash("Please enter email and password.")

            return redirect(
                url_for("login")
            )

        db = get_db()

        cursor = db.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email=%s
            """,
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user:

            if check_password_hash(
                user["password"],
                password
            ):

                session["user_id"] = user["id"]

                session["name"] = user["name"]

                session["role"] = user["role"]

                flash("Login successful!")

                return redirect(
                    url_for("index")
                )

        flash(
            "Invalid email or password."
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "login.html"
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Logged out successfully."
    )

    return redirect(
        url_for("index")
    )


# =========================
# PRODUCT DETAILS
# =========================

@app.route("/product/<int:product_id>")
def product_details(product_id):

    db = get_db()

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT *
        FROM products
        WHERE id=%s
        """,
        (product_id,)
    )

    product = cursor.fetchone()

    cursor.close()
    db.close()

    if not product:

        return "Product not found", 404

    return render_template(
        "product_details.html",
        product=product
    )


# =========================
# ADD TO CART
# =========================

@app.route("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):

    cart = session.get(
        "cart",
        {}
    )

    product_id = str(product_id)

    if product_id in cart:

        cart[product_id] += 1

    else:

        cart[product_id] = 1

    session["cart"] = cart

    flash(
        "Product added to cart!"
    )

    return redirect(
        request.referrer or
        url_for("index")
    )


# =========================
# CART
# =========================

@app.route("/cart")
def cart():

    cart = session.get(
        "cart",
        {}
    )

    products = []

    total = 0

    if cart:

        db = get_db()

        cursor = db.cursor(
            dictionary=True
        )

        ids = list(cart.keys())

        placeholders = ",".join(
            ["%s"] * len(ids)
        )

        query = f"""
        SELECT *
        FROM products
        WHERE id IN ({placeholders})
        """

        cursor.execute(
            query,
            ids
        )

        products = cursor.fetchall()

        cursor.close()
        db.close()

        for product in products:

            quantity = cart[
                str(product["id"])
            ]

            product["quantity"] = quantity

            product["subtotal"] = (
                float(product["price"])
                * quantity
            )

            total += product[
                "subtotal"
            ]

    return render_template(
        "cart.html",
        products=products,
        total=total
    )


# =========================
# REMOVE CART
# =========================

@app.route("/remove-from-cart/<int:product_id>")
def remove_from_cart(product_id):

    cart = session.get(
        "cart",
        {}
    )

    product_id = str(product_id)

    if product_id in cart:

        del cart[product_id]

    session["cart"] = cart

    return redirect(
        url_for("cart")
    )
# =========================
# CHECKOUT
# =========================

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():

    cart = session.get("cart", {})

    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for("cart"))

    if request.method == "POST":

        address = request.form.get("address")

        if not address:
            flash("Please enter your address.")
            return redirect(url_for("checkout"))

        db = get_db()

        cursor = db.cursor(dictionary=True)

        ids = list(cart.keys())

        placeholders = ",".join(["%s"] * len(ids))

        cursor.execute(
            f"""
            SELECT *
            FROM products
            WHERE id IN ({placeholders})
            """,
            ids
        )

        products = cursor.fetchall()

        total = 0

        for product in products:

            quantity = cart[str(product["id"])]

            total += float(product["price"]) * quantity

        # Create order

        cursor.execute(
            """
            INSERT INTO orders
            (user_id, total, address)
            VALUES (%s, %s, %s)
            """,
            (
                session["user_id"],
                total,
                address
            )
        )

        order_id = cursor.lastrowid

        # Add order items

        for product in products:

            quantity = cart[str(product["id"])]

            cursor.execute(
                """
                INSERT INTO order_items
                (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    order_id,
                    product["id"],
                    quantity,
                    product["price"]
                )
            )

            # Reduce stock

            cursor.execute(
                """
                UPDATE products
                SET stock = stock - %s
                WHERE id = %s
                """,
                (
                    quantity,
                    product["id"]
                )
            )

        db.commit()

        cursor.close()
        db.close()

        # Clear cart

        session["cart"] = {}

        flash("Order placed successfully! 🎉")

        return redirect(
            url_for("orders")
        )

    return render_template(
        "checkout.html"
    )
# =========================
# MY ORDERS
# =========================

@app.route("/orders")
@login_required
def orders():

    db = get_db()

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM orders
        WHERE user_id=%s
        ORDER BY id DESC
        """,
        (session["user_id"],)
    )

    orders = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "orders.html",
        orders=orders
    )
# =========================
# ADMIN DASHBOARD
# =========================

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():

    db = get_db()

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM products ORDER BY id DESC"
    )

    products = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin.html",
        products=products
    )
# =========================
# RUN SERVER
# =========================
@app.route("/admin/orders")
@admin_required
def admin_orders():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            orders.id,
            orders.user_id,
            orders.total,
            orders.address,
            orders.created_at
        FROM orders
        ORDER BY orders.id DESC
    """)

    orders = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_orders.html",
        orders=orders
    )
if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )
    