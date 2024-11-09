from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import binascii

app = Flask(__name__)
app.secret_key = binascii.hexlify(os.urandom(24)).decode()  # Needed for flash messages

# Database configuration
db_config = {
    'host': 'database-1.cjwme20sofql.us-east-1.rds.amazonaws.com',  # Your RDS endpoint
    'user': 'admin',  # Your DB username
    'password': 'air75095',  # Your DB password
    'database': 'freshbasket'
}

# Connection pool setup
cnxpool = MySQLConnectionPool(pool_name="mypool", pool_size=5, **db_config)

# Function to establish a database connection
def get_db_connection():
    try:
        return cnxpool.get_connection()
    except Error as err:
        print(f"Database Error: {err}")
        return None

@app.route('/')
def home():
    if 'user_id' in session:  # Check if the user is logged in
        return render_template('logged.html')  # Render logged-in version of home
    else:
        return render_template('home.html')  # Render normal home page
    
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('You have been logged out successfully!')
    return redirect(url_for('home'))  # Redirect to home after logout


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        mobile = request.form.get('mobile')
        email = request.form.get('email')
        password = generate_password_hash(request.form.get('password'))
        default_address = request.form.get('default_address')
        if not default_address:
            flash('Default address is required!')
            return redirect(url_for('register'))
        conn = get_db_connection()
        if not conn:
            flash('Database connection error.')
            return redirect(url_for('register'))
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO users (name, mobile, email, password, address) VALUES (%s, %s, %s, %s, %s)',
                (name, mobile, email, password, default_address)
            )
            conn.commit()
            flash('Thank you for registering!')
            return redirect(url_for('login'))
        except Error as e:
            flash(f"Error: {e}")
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        if not conn:
            flash('Database connection error.')
            return redirect(url_for('login'))
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                flash('Login successful!')
                return redirect(url_for('home'))
            else:
                flash('Invalid email or password!', 'error')  # Adding error flag for incorrect login
        except Error as e:
            flash(f"Error: {e}")
        finally:
            cursor.close()
            conn.close()
    return render_template('login.html')



@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()  # Get data sent via the fetch request
    user_id = data['user_id']
    item_id = data['item_id']
    item_name = data['item_name']
    item_price = data['item_price']
    quantity = data['quantity']

    # Update cart in the session
    cart_items = session.get('cart_items', [])
    item_found = False
    for item in cart_items:
        if item['item_id'] == item_id:
            item['quantity'] += quantity
            item_found = True
            break
    if not item_found:
        cart_items.append({
            'item_id': item_id,
            'item_name': item_name,
            'price': item_price,
            'quantity': quantity
        })
    session['cart_items'] = cart_items

    # Now insert the item into the cart_items table
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO cart_items (user_id, item_id, quantity) VALUES (%s, %s, %s)",
            (user_id, item_id, quantity)
        )
        conn.commit()
        return jsonify(success=True)
    except Error as e:
        conn.rollback()
        return jsonify(success=False, message=str(e))
    finally:
        cursor.close()
        conn.close()





@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('You need to log in to view your cart.')
        return redirect(url_for('login'))

    # Fetch the cart items from the database for the logged-in user
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT ci.item_id, ci.quantity, i.item_name, i.price FROM cart_items ci JOIN items i ON ci.item_id = i.item_id WHERE ci.user_id = %s', (session['user_id'],))
    cart_items_db = cursor.fetchall()
    cursor.close()
    conn.close()

    # Store cart items in session (optional)
    session['cart_items'] = cart_items_db

    return render_template('cart.html', cart_items=cart_items_db)



@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    if 'user_id' not in session:
        flash('You need to log in to remove items from the cart.')
        return redirect(url_for('login'))

    # Remove the item from the session cart_items
    cart_items = session.get('cart_items', [])
    cart_items = [item for item in cart_items if item['item_id'] != item_id]
    session['cart_items'] = cart_items

    # Remove from the database (cart_items table)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM cart_items WHERE user_id = %s AND item_id = %s', (session['user_id'], item_id))
        conn.commit()
    except Error as e:
        flash(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

    flash('Item removed from cart successfully!')
    return redirect(url_for('cart'))  # Redirect back to cart page



@app.route('/items', methods=['GET', 'POST'])
def items():
    if 'user_id' not in session:
        flash("Please log in to add items to your cart.")
        return redirect(url_for('login'))

    if request.method == "POST":
        item_name = request.form.get('name')
        item_price = float(request.form.get('price'))
        item_quantity = int(request.form.get('quantity'))
        cart_items = session.get('cart_items', [])
        for item in cart_items:
            if item['name'] == item_name:
                item['quantity'] += item_quantity
                break
        else:
            cart_items.append({'name': item_name, 'price': item_price, 'quantity': item_quantity})
        session['cart_items'] = cart_items
        flash(f"{item_name} added to your cart!")
        return redirect(url_for('items'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT item_id, item_name, price FROM items')
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    cart_items = session.get("cart_items", [])
    return render_template('items.html', items=items, cart_items=cart_items)


@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return jsonify(success=False, message="User not logged in")
    data = request.get_json()
    delivery_address = data.get('address', 'Default Address')
    payment_method = data["payment_method"]
    items = data['items']
    total_price = data['total_price']
    conn = get_db_connection()
    if not conn:
        return jsonify(success=False, message="Database connection error.")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO orders (user_id, delivery_address, payment_method, status, order_date, total_price) VALUES (%s, %s, %s, %s, %s, %s)",
            (session['user_id'], delivery_address, payment_method, 'Yet to Ship', datetime.now(), total_price)
        )
        order_id = cursor.lastrowid
        for item in items:
            cursor.execute(
                'INSERT INTO order_items (order_id, item_name, quantity, price) VALUES (%s, %s, %s, %s)',
                (order_id, item['name'], item['quantity'], item['price'])
            )
        conn.commit()
        return jsonify(success=True)
    except Error as e:
        conn.rollback()
        return jsonify(success=False, message=str(e))
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
