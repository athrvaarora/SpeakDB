import os
import psycopg2
from datetime import datetime, timedelta
import random
import uuid
import json

# Connect to the database
conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
cursor = conn.cursor()

# Create tables
print("Creating tables...")

# Drop tables if they exist
cursor.execute("""
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
""")

# Create customers table
cursor.execute("""
CREATE TABLE customers (
    customer_id VARCHAR(36) PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    address VARCHAR(200),
    city VARCHAR(50),
    state VARCHAR(20),
    zip_code VARCHAR(10),
    country VARCHAR(30),
    phone VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
""")

# Create categories table
cursor.execute("""
CREATE TABLE categories (
    category_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT
);
""")

# Create products table
cursor.execute("""
CREATE TABLE products (
    product_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category_id VARCHAR(36) REFERENCES categories(category_id),
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER NOT NULL,
    weight_kg DECIMAL(6, 2),
    dimensions VARCHAR(30),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
""")

# Create orders table
cursor.execute("""
CREATE TABLE orders (
    order_id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) REFERENCES customers(customer_id),
    order_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    shipping_address VARCHAR(200),
    shipping_city VARCHAR(50),
    shipping_state VARCHAR(20),
    shipping_zip VARCHAR(10),
    shipping_country VARCHAR(30),
    shipping_method VARCHAR(20),
    shipping_cost DECIMAL(10, 2),
    total_amount DECIMAL(10, 2) NOT NULL
);
""")

# Create order_items table
cursor.execute("""
CREATE TABLE order_items (
    item_id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) REFERENCES orders(order_id),
    product_id VARCHAR(36) REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    discount DECIMAL(5, 2) DEFAULT 0,
    subtotal DECIMAL(10, 2) NOT NULL
);
""")

# Sample data
print("Inserting sample data...")

# Categories
categories = [
    {"name": "Electronics", "description": "Electronic gadgets and devices"},
    {"name": "Clothing", "description": "Apparel and fashion items"},
    {"name": "Home & Kitchen", "description": "Home decor and kitchen accessories"},
    {"name": "Books", "description": "Books, e-books and reading materials"},
    {"name": "Toys & Games", "description": "Entertainment items for all ages"}
]

for category in categories:
    category_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO categories (category_id, name, description) VALUES (%s, %s, %s)",
        (category_id, category["name"], category["description"])
    )
    category["id"] = category_id

# Products
products = [
    # Electronics
    {"name": "Smartphone X", "category": "Electronics", "price": 799.99, "stock": 50, "weight": 0.25, "dimensions": "15x7x1 cm"},
    {"name": "Laptop Pro", "category": "Electronics", "price": 1299.99, "stock": 25, "weight": 1.8, "dimensions": "35x25x2 cm"},
    {"name": "Wireless Headphones", "category": "Electronics", "price": 149.99, "stock": 100, "weight": 0.3, "dimensions": "18x15x8 cm"},
    {"name": "Smart Watch", "category": "Electronics", "price": 249.99, "stock": 40, "weight": 0.1, "dimensions": "4x4x1 cm"},
    {"name": "Tablet Mini", "category": "Electronics", "price": 399.99, "stock": 30, "weight": 0.5, "dimensions": "20x15x0.8 cm"},
    
    # Clothing
    {"name": "Men's T-Shirt", "category": "Clothing", "price": 29.99, "stock": 200, "weight": 0.2, "dimensions": "30x20x2 cm"},
    {"name": "Women's Jeans", "category": "Clothing", "price": 59.99, "stock": 150, "weight": 0.6, "dimensions": "40x30x3 cm"},
    {"name": "Winter Jacket", "category": "Clothing", "price": 119.99, "stock": 50, "weight": 1.2, "dimensions": "60x40x10 cm"},
    {"name": "Running Shoes", "category": "Clothing", "price": 89.99, "stock": 70, "weight": 0.7, "dimensions": "30x20x15 cm"},
    {"name": "Summer Dress", "category": "Clothing", "price": 49.99, "stock": 80, "weight": 0.3, "dimensions": "45x35x2 cm"},
    
    # Home & Kitchen
    {"name": "Coffee Maker", "category": "Home & Kitchen", "price": 79.99, "stock": 40, "weight": 2.5, "dimensions": "30x25x40 cm"},
    {"name": "Knife Set", "category": "Home & Kitchen", "price": 49.99, "stock": 60, "weight": 1.8, "dimensions": "35x10x5 cm"},
    {"name": "Bed Sheets", "category": "Home & Kitchen", "price": 39.99, "stock": 100, "weight": 0.8, "dimensions": "30x25x5 cm"},
    {"name": "Toaster", "category": "Home & Kitchen", "price": 34.99, "stock": 45, "weight": 1.5, "dimensions": "30x15x20 cm"},
    {"name": "Blender", "category": "Home & Kitchen", "price": 69.99, "stock": 30, "weight": 3.0, "dimensions": "20x20x40 cm"},
    
    # Books
    {"name": "Mystery Novel", "category": "Books", "price": 14.99, "stock": 200, "weight": 0.5, "dimensions": "20x15x2 cm"},
    {"name": "Cookbook", "category": "Books", "price": 24.99, "stock": 80, "weight": 0.8, "dimensions": "25x20x2 cm"},
    {"name": "Science Fiction", "category": "Books", "price": 12.99, "stock": 150, "weight": 0.4, "dimensions": "18x12x2 cm"},
    {"name": "History Book", "category": "Books", "price": 19.99, "stock": 60, "weight": 0.9, "dimensions": "22x16x3 cm"},
    {"name": "Self-Help Guide", "category": "Books", "price": 16.99, "stock": 70, "weight": 0.5, "dimensions": "21x14x2 cm"},
    
    # Toys & Games
    {"name": "Board Game", "category": "Toys & Games", "price": 29.99, "stock": 40, "weight": 1.2, "dimensions": "30x30x5 cm"},
    {"name": "Action Figure", "category": "Toys & Games", "price": 19.99, "stock": 100, "weight": 0.3, "dimensions": "15x10x5 cm"},
    {"name": "Building Blocks", "category": "Toys & Games", "price": 39.99, "stock": 50, "weight": 2.0, "dimensions": "40x30x15 cm"},
    {"name": "Puzzle", "category": "Toys & Games", "price": 14.99, "stock": 60, "weight": 0.5, "dimensions": "25x25x3 cm"},
    {"name": "Remote Control Car", "category": "Toys & Games", "price": 49.99, "stock": 30, "weight": 1.0, "dimensions": "30x15x10 cm"}
]

for product in products:
    product_id = str(uuid.uuid4())
    category_id = next(cat["id"] for cat in categories if cat["name"] == product["category"])
    
    cursor.execute(
        """INSERT INTO products 
        (product_id, name, description, category_id, price, stock_quantity, weight_kg, dimensions, created_at, updated_at) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            product_id, 
            product["name"], 
            f"Description for {product['name']}", 
            category_id,
            product["price"],
            product["stock"],
            product["weight"],
            product["dimensions"],
            datetime.now() - timedelta(days=random.randint(1, 365)),
            datetime.now() - timedelta(days=random.randint(0, 30))
        )
    )
    
    product["id"] = product_id

# Customers
first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", 
               "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", 
              "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson"]
cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"]
states = ["NY", "CA", "IL", "TX", "AZ", "PA", "TX", "CA", "TX", "CA"]
countries = ["United States"] * 10

customers = []
for i in range(20):
    customer_id = str(uuid.uuid4())
    first_name = first_names[i]
    last_name = last_names[i]
    email = f"{first_name.lower()}.{last_name.lower()}@example.com"
    city_idx = i % 10
    
    cursor.execute(
        """INSERT INTO customers 
        (customer_id, first_name, last_name, email, address, city, state, zip_code, country, phone, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            customer_id,
            first_name,
            last_name,
            email,
            f"{random.randint(100, 999)} Main St",
            cities[city_idx],
            states[city_idx],
            f"{random.randint(10000, 99999)}",
            countries[city_idx],
            f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            datetime.now() - timedelta(days=random.randint(1, 365))
        )
    )
    
    customers.append({"id": customer_id, "first_name": first_name, "last_name": last_name})

# Orders and Order Items
statuses = ["Completed", "Processing", "Shipped", "Cancelled", "Refunded"]
shipping_methods = ["Standard", "Express", "Overnight", "Two-Day"]

# Generate 50 orders
for _ in range(50):
    order_id = str(uuid.uuid4())
    customer = random.choice(customers)
    status = random.choice(statuses)
    shipping_method = random.choice(shipping_methods)
    shipping_cost = float(random.randint(5, 20))
    order_date = datetime.now() - timedelta(days=random.randint(1, 180))
    
    # Each order will have 1-5 items
    num_items = random.randint(1, 5)
    selected_products = random.sample(products, num_items)
    total_amount = shipping_cost
    
    for product in selected_products:
        item_id = str(uuid.uuid4())
        quantity = random.randint(1, 3)
        unit_price = product["price"]
        discount = round(random.uniform(0, 0.2), 2)  # 0-20% discount
        subtotal = round(quantity * unit_price * (1 - discount), 2)
        total_amount += subtotal
        
    # Insert the order
    cursor.execute(
        """INSERT INTO orders 
        (order_id, customer_id, order_date, status, shipping_address, shipping_city, 
         shipping_state, shipping_zip, shipping_country, shipping_method, shipping_cost, total_amount) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            order_id,
            customer["id"],
            order_date,
            status,
            f"{random.randint(100, 999)} Main St",
            random.choice(cities),
            random.choice(states),
            f"{random.randint(10000, 99999)}",
            "United States",
            shipping_method,
            shipping_cost,
            round(total_amount, 2)
        )
    )
    
    # Insert the order items
    for product in selected_products:
        item_id = str(uuid.uuid4())
        quantity = random.randint(1, 3)
        unit_price = product["price"]
        discount = round(random.uniform(0, 0.2), 2)  # 0-20% discount
        subtotal = round(quantity * unit_price * (1 - discount), 2)
        
        cursor.execute(
            """INSERT INTO order_items 
            (item_id, order_id, product_id, quantity, unit_price, discount, subtotal) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                item_id,
                order_id,
                product["id"],
                quantity,
                unit_price,
                discount,
                subtotal
            )
        )

# Create useful views
cursor.execute("""
CREATE OR REPLACE VIEW order_details AS
SELECT 
    o.order_id,
    o.order_date,
    o.status,
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.email AS customer_email,
    oi.item_id,
    p.product_id,
    p.name AS product_name,
    cat.name AS category_name,
    oi.quantity,
    oi.unit_price,
    oi.discount,
    oi.subtotal,
    o.shipping_cost,
    o.total_amount
FROM 
    orders o
JOIN 
    customers c ON o.customer_id = c.customer_id
JOIN 
    order_items oi ON o.order_id = oi.order_id
JOIN 
    products p ON oi.product_id = p.product_id
JOIN 
    categories cat ON p.category_id = cat.category_id;
""")

cursor.execute("""
CREATE OR REPLACE VIEW product_sales AS
SELECT 
    p.product_id,
    p.name AS product_name,
    cat.name AS category_name,
    SUM(oi.quantity) AS total_quantity_sold,
    SUM(oi.subtotal) AS total_sales,
    COUNT(DISTINCT o.order_id) AS number_of_orders,
    COUNT(DISTINCT o.customer_id) AS number_of_customers
FROM 
    products p
JOIN 
    categories cat ON p.category_id = cat.category_id
LEFT JOIN 
    order_items oi ON p.product_id = oi.product_id
LEFT JOIN 
    orders o ON oi.order_id = o.order_id
GROUP BY 
    p.product_id, p.name, cat.name;
""")

cursor.execute("""
CREATE OR REPLACE VIEW customer_spending AS
SELECT 
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.email,
    c.city,
    c.state,
    c.country,
    COUNT(DISTINCT o.order_id) AS order_count,
    SUM(o.total_amount) AS total_spent,
    MAX(o.order_date) AS last_order_date,
    MIN(o.order_date) AS first_order_date
FROM 
    customers c
LEFT JOIN 
    orders o ON c.customer_id = o.customer_id
GROUP BY 
    c.customer_id, c.first_name, c.last_name, c.email, c.city, c.state, c.country;
""")

# Commit the changes
conn.commit()

# Close the connection
cursor.close()
conn.close()

print("Database setup completed successfully!")
print("\nTables created:")
print("- customers")
print("- categories")
print("- products")
print("- orders")
print("- order_items")
print("\nViews created:")
print("- order_details")
print("- product_sales")
print("- customer_spending")
print("\nSample data inserted into all tables.")
print("\nRetail database is ready for testing!")