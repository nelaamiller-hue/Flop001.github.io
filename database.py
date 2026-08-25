import sqlite3

connection = sqlite3.connect('library.db')

schema = """
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS borrows;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS shelves;


CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    admin BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT DEFAULT NULL,
    UNIQUE(name)
);
    CREATE TABLE rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room TEXT NOT NULL,
    location_id INTEGER NOT NULL,
    FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE CASCADE,
    UNIQUE(room, location_id)
);

    CREATE TABLE shelves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shelf INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
    UNIQUE(shelf, room_id)
);

CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);

CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    location_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    shelf_id INTEGER NOT NULL,
    FOREIGN KEY (location_id) REFERENCES locations (id),
    FOREIGN KEY (room_id) REFERENCES rooms (id),
    FOREIGN KEY (shelf_id) REFERENCES shelves (id)
);

CREATE TABLE borrows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    borrow BOOLEAN NOT NULL, 
    borrow_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    return_date TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books (id),
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);
"""

connection.executescript(schema)
connection.close()

print("Database has been prepared.")
