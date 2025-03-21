import os
import sqlite3
import datetime

# Ensure the data directory exists
os.makedirs('data', exist_ok=True)

# Create the SQLite database
db_path = 'data/test.db'
if os.path.exists(db_path):
    os.remove(db_path)  # Remove existing database

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    age INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    category TEXT,
    in_stock BOOLEAN DEFAULT 1
)
''')

cursor.execute('''
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (customer_id) REFERENCES customers (id)
)
''')

cursor.execute('''
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders (id),
    FOREIGN KEY (product_id) REFERENCES products (id)
)
''')

# Insert sample data
customers = [
    ('John Smith', 'john@example.com', 35),
    ('Sarah Johnson', 'sarah@example.com', 28),
    ('Michael Brown', 'michael@example.com', 42),
    ('Emma Davis', 'emma@example.com', 31),
    ('David Wilson', 'david@example.com', 45)
]

products = [
    ('Laptop', 1200.00, 'Electronics'),
    ('Smartphone', 800.00, 'Electronics'),
    ('Coffee Maker', 120.00, 'Home Appliances'),
    ('Desk Chair', 250.00, 'Furniture'),
    ('Headphones', 180.00, 'Electronics'),
    ('Desk Lamp', 45.00, 'Furniture'),
    ('Blender', 75.00, 'Home Appliances')
]

orders = [
    (1, 1980.00, 'completed'),
    (2, 800.00, 'shipped'),
    (3, 295.00, 'completed'),
    (4, 1200.00, 'pending'),
    (1, 255.00, 'shipped')
]

order_items = [
    (1, 1, 1, 1200.00),
    (1, 5, 1, 180.00),
    (1, 6, 2, 45.00),
    (1, 7, 1, 75.00),
    (2, 2, 1, 800.00),
    (3, 4, 1, 250.00),
    (3, 6, 1, 45.00),
    (4, 1, 1, 1200.00),
    (5, 4, 1, 250.00)
]

cursor.executemany("INSERT INTO customers (name, email, age) VALUES (?, ?, ?)", customers)
cursor.executemany("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", products)
cursor.executemany("INSERT INTO orders (customer_id, total_amount, status) VALUES (?, ?, ?)", orders)
cursor.executemany("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)", order_items)

# Commit changes and close connection
conn.commit()
conn.close()

print(f"SQLite database created successfully at {db_path}")