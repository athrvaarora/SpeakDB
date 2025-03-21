import os
import psycopg2
from psycopg2 import sql

# Get database connection info from environment variables
db_url = os.environ.get('DATABASE_URL')

# Connect to the database
conn = psycopg2.connect(db_url)
conn.autocommit = True
cursor = conn.cursor()

# Create tables
tables = [
    """
    CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE,
        age INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        category VARCHAR(50),
        in_stock BOOLEAN DEFAULT TRUE
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER REFERENCES customers(id),
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount DECIMAL(10, 2) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending'
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER REFERENCES orders(id),
        product_id INTEGER REFERENCES products(id),
        quantity INTEGER NOT NULL,
        price DECIMAL(10, 2) NOT NULL
    )
    """
]

# First check if tables already exist
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
existing_tables = [table[0] for table in cursor.fetchall()]

# Drop existing tables if they exist (in reverse order to handle foreign keys)
if 'order_items' in existing_tables:
    cursor.execute("DROP TABLE order_items")
if 'orders' in existing_tables:
    cursor.execute("DROP TABLE orders")
if 'products' in existing_tables:
    cursor.execute("DROP TABLE products")
if 'customers' in existing_tables:
    cursor.execute("DROP TABLE customers")

# Create tables
for table_query in tables:
    cursor.execute(table_query)

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

# Insert customers
cursor.executemany(
    "INSERT INTO customers (name, email, age) VALUES (%s, %s, %s)",
    customers
)

# Insert products
cursor.executemany(
    "INSERT INTO products (name, price, category) VALUES (%s, %s, %s)",
    products
)

# Get customer IDs to use in orders
cursor.execute("SELECT id FROM customers ORDER BY id")
customer_ids = [row[0] for row in cursor.fetchall()]

# Insert orders
orders_data = [
    (customer_ids[0], 1980.00, 'completed'),
    (customer_ids[1], 800.00, 'shipped'),
    (customer_ids[2], 295.00, 'completed'),
    (customer_ids[3], 1200.00, 'pending'),
    (customer_ids[0], 255.00, 'shipped')
]

cursor.executemany(
    "INSERT INTO orders (customer_id, total_amount, status) VALUES (%s, %s, %s)",
    orders_data
)

# Get order IDs and product IDs
cursor.execute("SELECT id FROM orders ORDER BY id")
order_ids = [row[0] for row in cursor.fetchall()]

cursor.execute("SELECT id FROM products ORDER BY id")
product_ids = [row[0] for row in cursor.fetchall()]

# Insert order items
order_items = [
    (order_ids[0], product_ids[0], 1, 1200.00),
    (order_ids[0], product_ids[4], 1, 180.00),
    (order_ids[0], product_ids[5], 2, 45.00),
    (order_ids[0], product_ids[6], 1, 75.00),
    (order_ids[1], product_ids[1], 1, 800.00),
    (order_ids[2], product_ids[3], 1, 250.00),
    (order_ids[2], product_ids[5], 1, 45.00),
    (order_ids[3], product_ids[0], 1, 1200.00),
    (order_ids[4], product_ids[3], 1, 250.00)
]

cursor.executemany(
    "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
    order_items
)

# Commit changes and close connection
conn.commit()
cursor.close()
conn.close()

print("PostgreSQL database initialized with test data")