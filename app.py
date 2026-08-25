import sqlite3

from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-very-secret-key-that-should-be-changed'

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, id, username, admin):
        self.id = id
        self.username = username
        self.admin = admin


def get_db_connection():
    conn = sqlite3.connect('library.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_admin():
    conn = sqlite3.connect('library.db')
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password, admin) VALUES (?, ?, ?)",
        ('admin', generate_password_hash('123'), 1)
    )
    conn.commit()
    conn.close()



@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user_row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user_row:
        return User(id=user_row['id'], username=user_row['username'], admin = user_row['admin'])
    return None


@app.route('/')
@login_required
def index():
    search_query= request.args.get('search', '')
    location_filter = request.args.getlist('location')
    sort_by = request.args.get('sort', 'default')

    to_search = "%" + search_query + "%"

    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
            SELECT b.id, b.title, b.author, l.name AS building_name, r.room AS room, s.shelf AS shelf, COALESCE(br.borrow, 0) AS borrow
            FROM books b
            JOIN locations l ON b.location_id = l.id
            LEFT JOIN rooms r ON b.room_id = r.id
            LEFT JOIN shelves s ON b.shelf_id = s.id
            LEFT JOIN borrows br ON br.book_id = b.id
            """
    store =[]
    conditions = []
    if search_query:
        conditions.append("(LOWER(b.title) LIKE LOWER(?) OR LOWER(b.author) LIKE LOWER(?))")
        store.append(f"%{search_query}%")
        store.append(f"%{search_query}%")

    if location_filter:
        placeholder = ", ".join(["?"] * len(location_filter))
        conditions.append(f"l.id IN ({placeholder})")
        store.extend(location_filter)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    if sort_by == 'author':
        query += " ORDER BY b.author, b.title;"
    elif sort_by == 'title':
        query += " ORDER BY b.title;"


    cursor.execute(query, store)
    books = cursor.fetchall()
    buildings = conn.execute("""SELECT id, name
                                FROM locations
                                ORDER BY name""").fetchall()

    conn.close()

    return render_template('index.html',
                           books=books,
                           search_query=search_query,
                           selected_location=location_filter,
                           buildings=buildings,
                           sort_by=sort_by)


@app.route('/login', methods=('GET', 'POST'))
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user_row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user_row and check_password_hash(user_row['password'], password):
            user = User(id=user_row['id'], username=user_row['username'], admin = user_row['admin'])
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add', methods=('GET', 'POST'))
@login_required
def add_book():
    conn = get_db_connection()
    locations = conn.execute('SELECT id, name FROM locations ORDER BY name').fetchall()

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        location_id = request.form['location']
        room_id = request.form.get('room')
        shelf_number = request.form['shelf']

        if not room_id:
            flash('Please select a room')
            return redirect(url_for('add_book'))

        shelf = conn.execute(
            "SELECT id FROM shelves WHERE shelf = ? AND room_id = ?",
            (shelf_number, room_id)
        ).fetchone()

        if shelf:
            shelf_id = shelf['id']
        else:
            cursor = conn.execute(
                "INSERT INTO shelves (shelf, room_id, location_id) VALUES (?, ?, ?)",
                (shelf_number, room_id, location_id)
            )
            shelf_id = cursor.lastrowid

        conn.execute(
            'INSERT INTO books (title, author, location_id, room_id, shelf_id) VALUES (?, ?, ?, ?, ?)',
            (title, author, location_id, room_id, shelf_id)
        )
        conn.commit()
        conn.close()
        flash('Book added')
        return redirect(url_for('index'))

    conn.close()
    return render_template('add.html', locations=locations)

@app.route('/move/<int:book_id>', methods=('GET', 'POST'))
@login_required
def move_book(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    locations = conn.execute('SELECT id, name FROM locations ORDER BY name').fetchall()

    if request.method == 'POST':
        new_location_id = request.form['location']
        new_room_id = request.form.get('room')
        new_shelf_number = request.form['shelf']

        if not new_room_id:
            flash('Please select a room')
            return redirect(url_for('add_book'))

        shelf = conn.execute(
            "SELECT id FROM shelves WHERE shelf = ? AND room_id = ?",
            (new_shelf_number, new_room_id)
        ).fetchone()

        if shelf:
            new_shelf_id = shelf['id']
        else:
            cursor = conn.execute(
                "INSERT INTO shelves (shelf, room_id, location_id) VALUES (?, ?, ?)",
                (new_shelf_number, new_room_id, new_location_id)
            )
            new_shelf_id = cursor.lastrowid

        conn.execute(
            'UPDATE books SET location_id = ?, room_id = ?, shelf_id = ? WHERE id = ?',
            (new_location_id, new_room_id, new_shelf_id, book_id)
        )
        conn.commit()
        conn.close()
        flash(f'Book "{book["title"]}" moved')
        return redirect(url_for('index'))

    conn.close()
    return render_template('move.html', book=book, locations=locations)

@app.route('/delete/<int:book_id>', methods=('POST',))
@login_required
def delete_book(book_id):

        conn = get_db_connection()

        book_1 = conn.execute('SELECT title FROM books WHERE id = ?', (book_id,)).fetchone()
        if not book_1:
            flash('ERROR')
            conn.close()
            return redirect(url_for('index'))

        conn.execute('DELETE FROM books where id = ?', (book_id,))
        conn.commit()
        flash(f'Book {book_1["title"]} deleted')
        conn.close()
        return redirect(url_for('index'))

@app.route('/index_buildings', methods=('GET', 'POST'))
@login_required
def index_buildings():
    search_query= request.args.get('search', '')

    to_search = "%" + search_query + "%"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute( """
            SELECT id, name, address
            FROM locations 
            WHERE name LIKE ?
            ORDER BY name
            """,(to_search,))
    store = []
    conditions = []
    if search_query:
        conditions.append("(LOWER(name) LIKE LOWER(?) OR LOWER(address) LIKE LOWER(?))")
        store.append(f"%{search_query}%")
        store.append(f"%{search_query}%")
    buildings = cursor.fetchall()
    conn.close()
    return render_template('index_buildings.html', buildings=buildings, search_query=search_query)


@app.route('/add_buildings', methods=('GET', 'POST'))
@login_required
def add_buildings():
        if request.method == 'POST':
            name = request.form['name']
            address = request.form['address']

            conn = get_db_connection()
            existing_room = conn.execute(
                'SELECT id FROM locations WHERE name = ? AND address = ?',
                (name, address,)
            ).fetchone()

            if existing_room:
                flash('Building already exists.')
            else:
                conn.execute(
                    'INSERT INTO locations (name, address) VALUES (?, ?)',
                    (name, address,)
                )

            conn.commit()
            conn.close()

            flash('Building added')
            return redirect(url_for('index_buildings'))

        return render_template('add_buildings.html')

@app.route('/delete_buildings/<int:building_id>', methods=('POST',))
@login_required
def delete_buildings(building_id):

        conn = get_db_connection()

        building_1 = conn.execute('SELECT name FROM locations WHERE id = ?', (building_id,)).fetchone()
        if not building_1:
            flash('ERROR')
            conn.close()
            return redirect(url_for('index'))

        conn.execute('DELETE FROM locations where id = ?', (building_id,))
        conn.commit()
        flash(f'Building {building_1["name"]} deleted')
        conn.close()
        return redirect(url_for('index_buildings'))

@app.route('/room_index/<int:building_id>', methods=('GET', 'POST'))
@login_required
def room_index(building_id):
    search_query= request.args.get('search', '')

    to_search = "%" + search_query + "%"

    conn = get_db_connection()
    cursor = conn.cursor()
    rooms = cursor.execute( """
            SELECT id, room
            FROM rooms 
            WHERE location_id = ?
                AND room LIKE ?
            ORDER BY room
            """,(building_id, to_search,)).fetchall()
    store = []
    conditions = []
    if search_query:
        conditions.append("(LOWER(room) LIKE LOWER(?)")
        store.append(f"%{search_query}%")
    conn.close()
    return render_template('room_index.html', rooms=rooms, building_id = building_id, search_query=search_query)

@app.route('/add_rooms/<int:building_id>', methods=('GET', 'POST'))
@login_required
def add_rooms(building_id):
        if request.method == 'POST':
            room = request.form['room']

            conn = get_db_connection()
            existing_room = conn.execute(
                'SELECT id FROM rooms WHERE room = ? AND location_id = ?',
                (room, building_id)
            ).fetchone()

            if existing_room:
                flash('Room already exists in this building.')
            else:
                conn.execute(
                    'INSERT INTO rooms (room, location_id) VALUES (?, ?)',
                    (room, building_id)
                )

            conn.commit()
            conn.close()

            flash('room added')
            return redirect(url_for('room_index', building_id=building_id))

        return render_template('add_rooms.html', building_id=building_id)

@app.route('/delete_rooms/<int:room_id>', methods=('POST',))
@login_required
def delete_rooms(room_id):

        conn = get_db_connection()

        room_1 = conn.execute('SELECT room, location_id FROM rooms WHERE id = ?', (room_id,)).fetchone()
        if not room_1:
            flash('ERROR')
            conn.close()
            return redirect(url_for('index_buildings'))

        conn.execute('DELETE FROM rooms where id = ?', (room_id,))
        conn.commit()
        flash(f'Room {room_1["room"]} deleted')
        conn.close()
        return redirect(url_for('room_index', building_id=room_1['location_id']))


@app.route('/index_customers', methods=('GET', 'POST'))
@login_required
def index_customers():
    search_query= request.args.get('search', '')

    to_search = "%" + search_query + "%"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute( """
            SELECT id, name, email
            FROM customers 
            WHERE name LIKE ?
            ORDER BY name
            """,(to_search,))
    store = []
    conditions = []
    if search_query:
        conditions.append("(LOWER(name) LIKE LOWER(?) OR LOWER(email) LIKE LOWER(?))")
        store.append(f"%{search_query}%")
        store.append(f"%{search_query}%")
    customers = cursor.fetchall()
    conn.close()
    return render_template('index_customers.html', customers=customers, search_query=search_query)


@app.route('/add_customers', methods=('GET', 'POST'))
@login_required
def add_customers():
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']

            conn = get_db_connection()

            existing_customer = conn.execute(
                'SELECT id FROM customers WHERE name = ?',
                (name,)
            ).fetchone()


            if existing_customer:
                flash('This customer exists')
                conn.commit()
            else:
                conn.execute('INSERT INTO customers (name, email ) VALUES(?,?)',
                             (name, email))
                conn.commit()
                conn.close()

                flash('customer added')
            return redirect(url_for('index_customers'))
        return render_template('add_customers.html')

@app.route('/delete_customers/<int:customer_id>', methods=('POST',))
@login_required
def delete_customers(customer_id):

        conn = get_db_connection()

        customers_1 = conn.execute('SELECT name FROM customers WHERE id = ?', (customer_id,)).fetchone()
        if not customers_1:
            flash('ERROR')
            conn.close()
            return redirect(url_for('index_customers'))

        conn.execute('DELETE FROM customers where id = ?', (customer_id,))
        conn.commit()
        flash(f'Customer {customers_1["name"]} deleted')
        conn.close()
        return redirect(url_for('index_customers'))

@app.route('/status/<int:book_id>', methods=('GET','POST',))
@login_required
def status(book_id):
    conn = get_db_connection()
    book = conn.execute("SELECT id, title, author FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book:
        flash('ERROR')
        conn.close()
        return redirect(url_for('index'))
    borrows = conn.execute("""
            SELECT bo.id, b.title AS book_title, b.author AS book_author, bo.borrow, bo.borrow_date, 
                   bo.return_date, c.name as customer_name, c.email as customer_email
            FROM borrows bo
                    JOIN customers c ON bo.customer_id = c.id 
                    JOIN books b ON bo.book_id = b.id
            WHERE bo.book_id = ?
            """,(book_id,)).fetchall()

    conn.close()
    return render_template('status.html', borrows = borrows, book=book)

@app.route('/edit_borrow/<int:book_id>', methods=('GET', 'POST',))
@login_required
def edit_borrow(book_id):

        conn = get_db_connection()

        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

        customers = conn.execute("SELECT id, name FROM customers ORDER BY name").fetchall()

        if request.method == 'POST':
            customer_id = request.form['customer_id']

            borrows = conn.execute("SELECT * FROM borrows WHERE book_id = ?", (book_id,)).fetchone()

            if borrows:
                conn.execute("""
                             UPDATE borrows
                             SET borrow = 1,
                                 customer_id = ?,
                                 borrow_date = datetime('now'),
                                 return_date = datetime('now', '+21 days')
                             WHERE book_id = ?
                             """, (customer_id, book_id))
            else:
                conn.execute("""
                             INSERT INTO borrows (book_id, customer_id, borrow, borrow_date, return_date)
                             VALUES (?, ?, 1, datetime('now'), datetime('now', '+21 days'))
                             """, (book_id, customer_id))

            conn.commit()
            conn.close()
            return redirect(url_for('status', book_id=book_id))

        conn.close()
        return render_template('edit_borrow.html', book=book, customers=customers)


@app.route('/return_b/<int:book_id>', methods=('POST',))
@login_required
def return_b(book_id):

        conn = get_db_connection()

        borrow = conn.execute("""
                              SELECT bo.id AS borrow_id, b.title AS book_title
                              FROM borrows bo
                                       JOIN books b ON bo.book_id = b.id
                              WHERE bo.book_id = ?
                              """, (book_id,)).fetchone()

        if not borrow:
            flash('ERROR')
            conn.close()
            return redirect(url_for('status', book_id=book_id))

        conn.execute('DELETE FROM borrows WHERE book_id = ?', (book_id,))
        conn.commit()
        flash(f'Book "{borrow["book_title"]}" returned')
        conn.close()

        return redirect(url_for('status', book_id=book_id))


@app.route('/api/rooms/<int:building_id>')
@login_required
def api_rooms(building_id):
    conn = get_db_connection()
    rooms = conn.execute(
        "SELECT id, room FROM rooms WHERE location_id = ? ORDER BY room",
        (building_id,)
    ).fetchall()
    conn.close()
    return {"rooms": [dict(r) for r in rooms]}

@app.route('/index_users', methods=('GET', 'POST'))
@login_required
def index_users():
    if not current_user.admin:
        flash("only admin can do that")
        return redirect(url_for('index'))
    search_query= request.args.get('search', '')

    to_search = "%" + search_query + "%"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute( """
            SELECT id, username
            FROM users 
            WHERE username LIKE ?
            ORDER BY username
            """,(to_search,))
    store = []
    conditions = []
    if search_query:
        conditions.append("(LOWER(username) LIKE LOWER(?))")
        store.append(f"%{search_query}%")
        store.append(f"%{search_query}%")
    users = cursor.fetchall()
    conn.close()
    return render_template('index_users.html', users=users, search_query=search_query)


@app.route('/add_users', methods=('GET', 'POST'))
@login_required
def add_users():
        if not current_user.admin:
            print(current_user.admin)
            print(current_user.id)
            print(current_user.username)
            flash("only admin can do that")
            return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

            if user:
                flash('Username already exists.')
            else:
                conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                             (username, generate_password_hash(password)))
                conn.commit()
                flash('User added')
            conn.close()

            return redirect(url_for('index_users'))
        return render_template('add_users.html')

@app.route('/delete_users/<int:user_id>', methods=('POST',))
@login_required
def delete_users(user_id):
        if not current_user.admin:
            flash("only admin can do that")
            return redirect(url_for('index'))

        conn = get_db_connection()

        user_1 = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user_1:
            flash('ERROR')
            conn.close()
            return redirect(url_for('index_users'))

        if user_1["id"] == current_user.id:
            flash("ERROR, cannot delete yourself")
            conn.close()
            return redirect(url_for('index_users'))

        conn.execute('DELETE FROM users where id = ?', (user_id,))
        conn.commit()
        flash(f'User {user_1["username"]} deleted')
        conn.close()
        return redirect(url_for('index_users'))


if __name__ == '__main__':
    create_admin()
    app.run(debug=False)
