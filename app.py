from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "secret123"
app.permanent_session_lifetime = timedelta(days=7)

# ---------------- DATABASE HELPER ----------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- HOME PAGE ----------------
@app.route('/')
def index():
    db = get_db()
    products = db.execute("SELECT * FROM products").fetchall()
    grocery = db.execute("SELECT * FROM grocery").fetchall()
    painting = db.execute("SELECT * FROM painting").fetchall()
    db.close()
    return render_template("index.html", products=products,grocery=grocery,painting=painting,user=session.get('user'))

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    if 'user' in session:
        return redirect('/')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        name=request.form['name']


        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user:
            db.close()
            return "Username already exists!"
        db.execute("INSERT INTO users(username,password,email,phone,name) VALUES(?,?,?,?,?)",
                   (username,password,email,phone,name))
        db.commit()
        db.close()
        return redirect('/login')
    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if 'user' in session:
        return redirect('/')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=? AND password=?", 
                          (username,password)).fetchone()
        db.close()
        if user:
            session.permanent = True
            session['user'] = username
            if 'cart' not in session:
                session['cart'] = {}  # initialize as dictionary
            return redirect('/')
        return "Invalid credentials"
    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- ADD TO CART ----------------
@app.route('/add_to_cart/<ptype>/<int:pid>')
def add_to_cart(ptype, pid):
    if 'user' not in session:
        return redirect('/login')

    if 'cart' not in session or not isinstance(session['cart'], dict):
        session['cart'] = {}

    qty = int(request.args.get('qty', 1))
    key = f"{ptype}_{pid}"

    if key in session['cart']:
        session['cart'][key] += qty
    else:
        session['cart'][key] = qty

    session.modified = True
    return redirect('/cart')



@app.route('/remove_from_cart/<ptype>/<int:pid>')
def remove_from_cart(ptype, pid):
    key = f"{ptype}_{pid}"
    if key in session.get('cart', {}):
        session['cart'][key] -= 1
        if session['cart'][key] <= 0:
            del session['cart'][key]
    session.modified = True
    return redirect('/cart')


@app.route('/delete_from_cart/<ptype>/<int:pid>')
def delete_from_cart(ptype, pid):
    key = f"{ptype}_{pid}"
    session['cart'].pop(key, None)
    session.modified = True
    return redirect('/cart')



@app.route('/cart')
def cart():
    if 'user' not in session:
        return redirect('/login')

    cart_items = []
    total = 0
    db = get_db()

    for key, qty in session.get('cart', {}).items():
        ptype, pid = key.split('_')

        if ptype == 'product':
            item = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        elif ptype == 'grocery':
            item = db.execute("SELECT * FROM grocery WHERE id=?", (pid,)).fetchone()
        elif ptype == 'painting':
            item = db.execute("SELECT * FROM painting WHERE id=?", (pid,)).fetchone()
        else:
            continue

        if item:
            subtotal = item['price'] * qty
            total += subtotal

            cart_items.append({
                'id': item['id'],
                'type': ptype,
                'name': item['name'],
                'price': item['price'],
                'qty': qty,
                'subtotal': subtotal
            })

    db.close()
    return render_template('cart.html', products=cart_items, total=total)




@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user' not in session or not session.get('cart'):
        return redirect('/login')

    db = get_db()

    # ---------- PLACE ORDER ----------
    if request.method == 'POST':
        for key, qty in session['cart'].items():
            item_type, item_id = key.split('_')

            if item_type == 'product':
                item = db.execute("SELECT * FROM products WHERE id=?", (item_id,)).fetchone()
            elif item_type == 'painting':
                item = db.execute("SELECT * FROM painting WHERE id=?", (item_id,)).fetchone()
            else:
                item = db.execute("SELECT * FROM grocery WHERE id=?", (item_id,)).fetchone()

            if item:
                db.execute("""
                    INSERT INTO orders(username, product_id, product_name, price, quantity)
                    VALUES(?,?,?,?,?)
                """, (
                    session['user'],
                    item['id'],
                    item['name'],
                    item['price'],
                    qty
                ))

        db.commit()
        db.close()
        session['cart'] = {}
        return "✅ Order placed successfully!"

    # ---------- SHOW CHECKOUT PAGE ----------
    cart_items = []
    total = 0

    for key, qty in session['cart'].items():
        item_type, item_id = key.split('_')

        if item_type == 'product':
            item = db.execute("SELECT * FROM products WHERE id=?", (item_id,)).fetchone()
        elif item_type == 'painting':
            item = db.execute("SELECT * FROM painting WHERE id=?", (item_id,)).fetchone()
        else:
            item = db.execute("SELECT * FROM grocery WHERE id=?", (item_id,)).fetchone()

        if item:
            cart_items.append({
                'name': item['name'],
                'price': item['price'],
                'qty': qty
            })
            total += item['price'] * qty

    db.close()
    return render_template('checkout.html', products=cart_items, total=total)


# ---------------- PROFILE PAGE ----------------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        return redirect('/login')

    db = get_db()

    if request.method == 'POST':
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        if password.strip() == "":
            db.execute("""
                UPDATE users SET email=?, phone=?
                WHERE username=?
            """, (email, phone, session['user']))
        else:
            db.execute("""
                UPDATE users SET email=?, phone=?, password=?
                WHERE username=?
            """, (email, phone, password, session['user']))

        db.commit()

    user = db.execute(
        "SELECT * FROM users WHERE username=?",
        (session['user'],)
    ).fetchone()
    orders = db.execute("SELECT * FROM orders WHERE username=?", (session['user'],)).fetchall()

    db.close()
    return render_template('profile.html', user=user,orders=orders)


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()
        db.close()

        if user:
            # store email temporarily
            session['reset_email'] = email
            return redirect('/reset-password')
        else:
            return "Email not found"

    return render_template('forgot_password.html')
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password(): 
    if 'reset_email' not in session:
        return redirect('/forgot-password')

    if request.method == 'POST':
        new_password = request.form['new_password']
        email = session['reset_email']

        db = get_db()
        db.execute(
            "UPDATE users SET password=? WHERE email=?",
            (new_password, email)
        )
        db.commit()
        db.close()

        # clear the temporary email from session
        session.pop('reset_email', None)

        return redirect('/login')

    return render_template('reset_password.html')



# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)
